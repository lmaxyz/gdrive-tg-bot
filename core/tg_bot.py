import logging
import asyncio
import time
import traceback
import json

from pyrogram import Client, filters
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Message,
    CallbackQuery,
)

from aiogoogle import Aiogoogle
from aiogoogle.auth.utils import create_secret
from aiogoogle.auth.creds import UserCreds

from core.db import DBClient
from settings import APP_API_HASH, APP_CLIENT_ID, BOT_TOKEN, G_APP_CREDS
from core.exceptions import AuthenticationTimeout


_logger = logging.getLogger(__name__)


class BotManager:
    def __init__(self, db_client: DBClient, google_client: Aiogoogle):
        self._bot_client = Client("gdrive_tg_bot", APP_CLIENT_ID, APP_API_HASH, bot_token=BOT_TOKEN)
        self._google_client = google_client
        self._db_client = db_client

        self.__register_handlers()

    def __register_handlers(self):
        self._bot_client.add_handler(MessageHandler(self._save_to_google_drive, filters.media))
        self._bot_client.add_handler(CallbackQueryHandler(self._make_file_public))

    async def _authenticate_user(self, message):
        if (user_creds := await self._db_client.get_user_creds(message.chat.id)) is not None:
            if self._google_client.oauth2.is_expired(user_creds):
                try:
                    user_creds = await self._google_client.oauth2.refresh(user_creds)
                    await self._db_client.save_user_creds(json.dumps(user_creds), user_id=message.chat.id)
                except Exception:
                    _logger.error(traceback.format_exc())
                    await self._db_client.delete_auth(message.chat.id)
                else:
                    return user_creds
            else:
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
        secret = create_secret()
        await self._db_client.init_auth(message.chat.id, secret)

        uri = self._google_client.oauth2.authorization_url(
            client_creds=G_APP_CREDS,
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

    async def _make_file_public(self, _app, callback: CallbackQuery):
        file_id = callback.data

        if (user_creds := await self._authenticate_user(callback.message)) is not None:
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

        else:
            await callback.message.reply("❌ Authentication failed.\nTry again later.")

    async def _save_to_google_drive(self, app, message: Message):
        if (user_creds := await self._authenticate_user(message)) is not None:
            try:
                await self._upload_file_to_google_drive(app, message, user_creds)
            except Exception:
                await message.reply("❌ I can't save it right now. But you can come later and I hope I'll do it.")
                _logger.error(traceback.format_exc())

        else:
            await message.reply("❌ Authentication failed.\nTry again later.")

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
