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
from core.google.auth import GoogleAuthenticator
from core.google.drive import GDriveClient

from .decorators import with_user_authentication
from .types import HandlerType


_logger = logging.getLogger(__name__)


class BotManager:
    _AUTHORIZATION_MESSAGE = "Please authorize in our app with your google account.\nYou have 2 minutes."
    _HELP_MESSAGE = "ToDo"

    def __init__(self, db_client: DBClient, google_client: Aiogoogle):
        self._bot_client = Client("gdrive_tg_bot", APP_CLIENT_ID, APP_API_HASH, bot_token=BOT_TOKEN)
        self._db_client = db_client

        self._google_client = google_client
        self._authenticator = GoogleAuthenticator(self, self._db_client, self._google_client)
        self._gdrive_client = GDriveClient(self._google_client, self._db_client)

        self.__register_handlers()

    @property
    def authenticator(self):
        return self._authenticator

    def __register_handlers(self):
        self._bot_client.add_handler(MessageHandler(self._save_to_google_drive, filters.media))
        self._bot_client.add_handler(MessageHandler(self._set_saving_folder, filters.command("set_saving_folder")))
        self._bot_client.add_handler(MessageHandler(self._create_folder, filters.command("create_folder")))
        self._bot_client.add_handler(CallbackQueryHandler(self._make_file_public))

    async def send_authorization_request(self, user_id, authorization_url):
        reply_markup = InlineKeyboardMarkup([[
            InlineKeyboardButton("Authorize", url=authorization_url),
        ]])
        await self._bot_client.send_message(user_id, self._AUTHORIZATION_MESSAGE, reply_markup=reply_markup)

    @with_user_authentication(HandlerType.Message)
    async def _upload_file_to_google_drive(self, _app: Client, message: Message, user_creds: dict):
        file_name = message.document.file_name
        _logger.info(f"[+] Start downloading '{file_name}'")
        process_message = await message.reply("Start file downloading...")

        file = await self._bot_client.download_media(message.document, in_memory=True, progress_args=(process_message,),
                                                     progress=_update_downloading_progress)
        parent_folder_id = await self._db_client.get_saving_folder_id(message.from_user.id)

        await process_message.edit_text("Uploading to Google Drive...")
        upload_response = await self._gdrive_client.upload_file(
            InMemoryFile(file_name, message.document.mime_type, file.getbuffer()),
            user_creds,
            parent_folder_id
        )

        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("View File", url=upload_response['webViewLink'])],
            [InlineKeyboardButton("Download File", url=upload_response['webContentLink'])],
            [InlineKeyboardButton("Make File public", callback_data=upload_response['id'])]
        ])

        await process_message.edit_text(f"✅ File **{file_name}** uploaded successfully.",
                                        reply_markup=reply_markup)

    @with_user_authentication(HandlerType.Message)
    async def _set_saving_folder(self, _app, message: Message, user_creds):
        try:
            folder_name = message.text.split()[1]
        except IndexError:
            await message.reply("❌ You have to send this command with folder name.\n"
                                "  Example: `/set_saving_folder {folder_name}`")

        else:
            if (folder_id := await self._gdrive_client.get_folder_id(folder_name, user_creds)) is not None:
                await self._db_client.set_saving_folder_id(message.from_user.id, folder_id)
                await message.reply(f"✅ Saving folder is changed to {folder_name}")
            else:
                await message.reply("❌ Folder doesn't exists.\n"
                                    "  Try to create new one with the next command: `/create_folder {folder_name}`")

    @with_user_authentication(HandlerType.Message)
    async def _create_folder(self, _app, message, user_creds):
        try:
            folder_name = message.text.split()[1]
        except IndexError:
            await message.reply("❌ You have to send this command with folder name.\n"
                                "  Example: `/create_folder {folder_name}`")
        else:
            parent_folder = await self._db_client.get_saving_folder_id(message.from_user.id)
            if (folder_id := await self._gdrive_client.create_folder(folder_name, user_creds, parent_folder)) is not None:
                await message.reply(f"✅ Folder `{folder_name}` successfully created.")
            else:
                await message.reply(f"❌ Can't create folder `{folder_name}` right now.")

    @with_user_authentication(HandlerType.Callback)
    async def _make_file_public(self, _app, callback: CallbackQuery, user_creds: dict):
        try:
            await self._gdrive_client.make_file_public(callback.data, user_creds)

        except Exception:
            _logger.error(traceback.format_exc())
            await callback.message.reply("❌ Failed to make file public. Try again later.")

        else:
            await callback.answer("🚀 File can be shared now.")

    async def _save_to_google_drive(self, app, message: Message):
        try:
            await self._upload_file_to_google_drive(app, message)
        except Exception:
            await message.reply("❌ I can't save it right now. But you can come later and I hope I'll do it.")
            _logger.error(traceback.format_exc())

    async def start_tg_bot(self):
        await self._bot_client.start()
        _logger.debug('[+] Started.')

    async def stop_tg_bot(self):
        _logger.debug('[*] Stopping db client...')
        await self._db_client.disconnect()

        _logger.debug('[*] Stopping bot client...')
        await self._bot_client.stop()

        _logger.debug('[+] Stopped.')


class InMemoryFile:
    def __init__(self, name, mime_type, mem_link):
        self._name = name
        self._mime_type = mime_type
        self._mem_link = mem_link

    @property
    def name(self):
        return self._name

    @property
    def mime_type(self):
        return self._mime_type

    def read(self):
        return bytes(self._mem_link)


async def _update_downloading_progress(current, total, progress_tracking_message):
    await progress_tracking_message.edit_text(f"Downloading from Telegram...\n**{current * 100 / total:.1f}%**")
