import logging

from pyrogram import Client, filters
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from aiogoogle import Aiogoogle

from settings import APP_API_HASH, APP_CLIENT_ID, BOT_TOKEN
from core.db import DBClient

from .handlers import (
    upload_file_to_google_drive,
    make_file_public,
    create_folder,
    set_saving_folder,
    help_message
)

_logger = logging.getLogger(__name__)


class GoogleDriveManager(Client):
    _AUTHORIZATION_MESSAGE = "Please authorize in our app with your google account.\nYou have 2 minutes."

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
        self.add_handler(MessageHandler(upload_file_to_google_drive, filters.document))
        self.add_handler(MessageHandler(set_saving_folder, filters.command("set_saving_folder")))
        self.add_handler(MessageHandler(create_folder, filters.command("create_folder")))
        self.add_handler(MessageHandler(help_message, filters.command("help")))
        self.add_handler(CallbackQueryHandler(make_file_public))

    async def send_authorization_request(self, user_id, authorization_url):
        reply_markup = InlineKeyboardMarkup([[
            InlineKeyboardButton("Authorize", url=authorization_url),
        ]])
        await self.send_message(user_id, self._AUTHORIZATION_MESSAGE, reply_markup=reply_markup)
