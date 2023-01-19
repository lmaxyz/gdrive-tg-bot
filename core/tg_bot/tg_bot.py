import logging
import traceback

from pyrogram import Client, filters
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Message,
    CallbackQuery,
)

from aiogoogle import Aiogoogle
from aiogoogle.auth.creds import UserCreds


from settings import APP_API_HASH, APP_CLIENT_ID, BOT_TOKEN

from core.db import DBClient
from core.google.auth import GoogleAuthenticator

from .decorators import with_user_authentication
from .types import HandlerType


_logger = logging.getLogger(__name__)


class BotManager:
    _AUTHORIZATION_MESSAGE = "Please authorize in our app with your google account.\nYou have 2 minutes."

    def __init__(self, db_client: DBClient, google_client: Aiogoogle):
        self._bot_client = Client("gdrive_tg_bot", APP_CLIENT_ID, APP_API_HASH, bot_token=BOT_TOKEN)
        self._db_client = db_client

        self._google_client = google_client
        self._authenticator = GoogleAuthenticator(self, self._db_client, self._google_client)

        self.__register_handlers()

    @property
    def authenticator(self):
        return self._authenticator

    def __register_handlers(self):
        self._bot_client.add_handler(MessageHandler(self._save_to_google_drive, filters.media))
        self._bot_client.add_handler(CallbackQueryHandler(self._make_file_public))

    async def send_authorization_request(self, user_id, authorization_url):
        reply_markup = InlineKeyboardMarkup([[
            InlineKeyboardButton("Authorize", url=authorization_url),
        ]])
        await self._bot_client.send_message(user_id, self._AUTHORIZATION_MESSAGE, reply_markup=reply_markup)

    @with_user_authentication(HandlerType.Message)
    async def _upload_file_to_google_drive(self, app: Client, message, user_creds: dict):
        file_name = message.document.file_name
        _logger.info(f"[+] Start downloading '{file_name}'")
        file = await app.download_media(message.document.file_id, in_memory=True)

        metadata = {
            'name': file_name,
            'mimeType': message.document.mime_type
        }

        async with self._google_client as google:
            drive_v3 = await google.discover('drive', 'v3')

            upload_request = drive_v3.files.create(
                pipe_from=_CustomFileBuffer(file.getbuffer()),
                json=metadata,
                fields='id,name,webContentLink,webViewLink'
            )

            upload_response = await google.as_user(upload_request, user_creds=UserCreds(**user_creds))

            reply_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("View File", url=upload_response['webViewLink'])],
                [InlineKeyboardButton("Download File", url=upload_response['webContentLink'])],
                [InlineKeyboardButton("Make File public", callback_data=upload_response['id'])]
            ])

            await message.reply(f"✅ File **{file_name}** uploaded successfully.", reply_markup=reply_markup)

    @with_user_authentication(HandlerType.Callback)
    async def _make_file_public(self, _app, callback: CallbackQuery, user_creds: dict):
        file_id = callback.data

        try:
            async with self._google_client as google:
                drive_v3 = await google.discover('drive', 'v3')
                update_request = drive_v3.permissions.create(
                    fileId=file_id,
                    json={'type': 'anyone', 'role': 'reader'}
                )
                await google.as_user(update_request, user_creds=user_creds)

        except Exception:
            _logger.error(traceback.format_exc())
            await callback.message.reply("❌ Failed to make file public. Try again later.")

        else:
            await callback.message.reply("🚀 File can be shared now.")

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


class _CustomFileBuffer:
    _mem_link = None

    def __init__(self, mem_link):
        self._mem_link = mem_link

    def read(self):
        return bytes(self._mem_link)
