import logging
import traceback

from pyrogram import Client, filters
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    Message,
)

from aiogoogle import Aiogoogle

from settings import APP_API_HASH, APP_CLIENT_ID, BOT_TOKEN

from core.db import DBClient

from .decorators import with_google_session
from .types import HandlerType
from .file import InMemoryFile


_logger = logging.getLogger(__name__)


class GoogleDriveManager(Client):
    _AUTHORIZATION_MESSAGE = "Please authorize in our app with your google account.\nYou have 2 minutes."
    _HELP_MESSAGE = "ToDo"

    def __init__(self, db_client: DBClient, google_client: Aiogoogle):
        super().__init__("gdrive_tg_bot", APP_CLIENT_ID, APP_API_HASH, bot_token=BOT_TOKEN)
        self._db_client = db_client
        self._google_client = google_client
        self.__register_handlers()

    @property
    def db_client(self):
        return self._db_client

    @property
    def google(self):
        return self._google_client

    def __register_handlers(self):
        self.add_handler(MessageHandler(_upload_file_to_google_drive, filters.document))
        self.add_handler(MessageHandler(_set_saving_folder, filters.command("set_saving_folder")))
        self.add_handler(MessageHandler(_create_folder, filters.command("create_folder")))
        self.add_handler(CallbackQueryHandler(_make_file_public))

    async def send_authorization_request(self, user_id, authorization_url):
        reply_markup = InlineKeyboardMarkup([[
            InlineKeyboardButton("Authorize", url=authorization_url),
        ]])
        await self.send_message(user_id, self._AUTHORIZATION_MESSAGE, reply_markup=reply_markup)


@with_google_session(HandlerType.Message)
async def _upload_file_to_google_drive(app: GoogleDriveManager, message: Message):
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
async def _set_saving_folder(app: GoogleDriveManager, message: Message):
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
async def _create_folder(app: GoogleDriveManager, message: Message):
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
async def _make_file_public(_app: GoogleDriveManager, callback: CallbackQuery):
    try:
        await callback.from_user.google_session.drive.make_file_public(callback.data)

    except Exception:
        _logger.error(traceback.format_exc())
        await callback.message.reply("❌ Failed to make file public. Try again later.")

    else:
        await callback.answer("🚀 File can be shared now.")


async def _update_downloading_progress(current, total, progress_tracking_message):
    await progress_tracking_message.edit_text(f"Downloading from Telegram...\n**{current * 100 / total:.1f}%**")
