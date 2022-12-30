import logging
import asyncio
import time

from pyrogram import Client, filters
from pyrogram.handlers import MessageHandler
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Message,
)

from aiogoogle import Aiogoogle
from aiogoogle.auth.utils import create_secret
from aiogoogle.auth.creds import UserCreds

from db import DBClient
from settings import APP_API_HASH, APP_CLIENT_ID, BOT_TOKEN, CREDS
from exceptions import AuthenticationTimeout


_logger = logging.getLogger(__name__)


class BotManager:
    def __init__(self, db_client: DBClient, google_client: Aiogoogle):
        self._bot_client = Client("gdrive_book_saver", APP_CLIENT_ID, APP_API_HASH, bot_token=BOT_TOKEN)
        self._google_client = google_client
        self._db_client = db_client

        self.__register_handlers()

    def __register_handlers(self):
        self._bot_client.add_handler(MessageHandler(self._save_to_google_drive, filters.media))

    async def _authenticate_user(self, message):
        if (user_creds := await self._db_client.get_user_creds(message.chat.id)) is not None:
            return user_creds

        await self._init_authorization(message)

        try:
            return await self._wait_for_authorization(message)
        except AuthenticationTimeout:
            await self._db_client.delete_auth(message.chat.id)
            return None

    async def _wait_for_authorization(self, message, timeout: float = 120.0):
        start_time = time.time()

        while True:
            if (user_creds := await self._db_client.get_user_creds(message.chat.id)) is not None:
                return user_creds

            if time.time() - start_time >= timeout:
                raise AuthenticationTimeout("Authentication haven't done.")

            await asyncio.sleep(5.0)

    async def _init_authorization(self, message):
        if self._google_client.oauth2.is_ready(CREDS):
            secret = create_secret()
            await self._db_client.init_auth(message.chat.id, secret)

            uri = self._google_client.oauth2.authorization_url(
                client_creds=CREDS,
                state=secret,
                access_type="offline",
                include_granted_scopes=True,
                prompt="select_account",
            )
            reply_markup = InlineKeyboardMarkup([[
                InlineKeyboardButton("Authorize", url=uri),
            ]])
            await message.reply("Please authorize in our app with your google account.\nYou have 2 minutes.",
                                reply_markup=reply_markup)

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

            await google.as_user(
                drive_v3.files.create(pipe_from=_CustomFileBuffer(file.getbuffer()), json=metadata),
                user_creds=UserCreds(**user_creds)
            )

    async def _save_to_google_drive(self, app, message: Message):
        if (user_creds := await self._authenticate_user(message)) is not None:
            await self._upload_file_to_google_drive(app, message, user_creds)
        else:
            await message.reply("Authentication failed.\nTry again later.")

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
