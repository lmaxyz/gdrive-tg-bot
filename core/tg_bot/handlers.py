import logging
import traceback

from pyrogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton

from .decorators import with_google_session
from .types import HandlerType
from .file import InMemoryFile

from settings import HELP_MESSAGE


_logger = logging.getLogger(__name__)


@with_google_session(HandlerType.Message)
async def upload_file_to_google_drive(app, message: Message):
    file_name = message.document.file_name
    _logger.info(f"[+] Start downloading '{file_name}'")
    process_message = await message.reply("Start file downloading...")

    file = await app.download_media(message.document, in_memory=True, progress_args=(process_message,),
                                                 progress=_update_downloading_progress)
    parent_folder_id = await app.db_client.get_saving_folder_id(message.from_user.id)

    await process_message.edit_text("Uploading to Google Drive...")
    upload_response = await message.from_user.google_session.drive.upload_file(
        InMemoryFile(file_name, message.document.mime_type, file.getbuffer()),
        parent_folder_id
    )

    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("View File", url=upload_response['webViewLink'])],
        [InlineKeyboardButton("Download File", url=upload_response['webContentLink'])],
        [InlineKeyboardButton("Make File public", callback_data=upload_response['id'])]
    ])

    await process_message.edit_text(f"✅ File **{file_name}** uploaded successfully.",
                                    reply_markup=reply_markup)


@with_google_session(HandlerType.Message)
async def set_saving_folder(app, message: Message):
    try:
        folder_name = message.text.split()[1]
    except IndexError:
        await message.reply("❌ You have to send this command with folder name.\n"
                            "  Template: `/set_saving_folder {folder_name}`")

    else:
        if (folder_id := await message.from_user.google_session.drive.get_folder_id(folder_name)) is not None:
            await app.db_client.set_saving_folder_id(message.from_user.id, folder_id)
            await message.reply(f"✅ Saving folder is changed to {folder_name}")
        else:
            await message.reply("❌ Folder doesn't exists.\n"
                                "  Try to create new one with the next command: `/create_folder {folder_name}`")


@with_google_session(HandlerType.Message)
async def create_folder(app, message: Message):
    try:
        folder_name = message.text.split()[1]
    except IndexError:
        await message.reply("❌ You have to send this command with folder name.\n"
                            "  Template: `/create_folder {folder_name}`")
    else:
        parent_folder = await app.db_client.get_saving_folder_id(message.from_user.id)
        # Maybe folder_id will be used later.
        google_drive = message.from_user.google_session.drive
        if (_folder_id := await google_drive.create_folder(folder_name, parent_folder)) is not None:
            await message.reply(f"✅ Folder `{folder_name}` successfully created.")
        else:
            await message.reply(f"❌ Can't create folder `{folder_name}` right now.")


@with_google_session(HandlerType.Callback)
async def make_file_public(_app, callback: CallbackQuery):
    try:
        await callback.from_user.google_session.drive.make_file_public(callback.data)

    except Exception:
        _logger.error(traceback.format_exc())
        await callback.message.reply("❌ Failed to make file public. Try again later.")

    else:
        await callback.answer("🚀 File can be shared now.")


async def help_message(_app, message: Message):
    await message.reply(HELP_MESSAGE)


async def _update_downloading_progress(current, total, progress_tracking_message):
    await progress_tracking_message.edit_text(f"Downloading from Telegram...\n**{current * 100 / total:.1f}%**")