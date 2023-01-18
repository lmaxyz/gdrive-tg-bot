from aiohttp.web import Application
from aiogoogle import Aiogoogle

from settings import DB_FILE_NAME, G_APP_CREDS

from core.db import DBClient
from core.tg_bot import BotManager


async def _db_connect(application: Application):
    application['db_client'] = await DBClient.connect(DB_FILE_NAME)


async def _init_google_client(application: Application):
    google_client = Aiogoogle(client_creds=G_APP_CREDS)

    if not google_client.oauth2.is_ready(G_APP_CREDS):
        raise ValueError("Bad google app credentials.")

    application['google_client'] = google_client


async def _start_tg_bot(application: Application):
    bot_manager = BotManager(application['db_client'], application['google_client'])
    await bot_manager.start_tg_bot()
    application['bot_manager'] = bot_manager


startup_actions = (
    _db_connect,
    _init_google_client,
    _start_tg_bot,
)
