import sys
import logging

from aiohttp import web
from aiogoogle import Aiogoogle

from settings import DB_FILE_NAME, APP_API_HASH, APP_CLIENT_ID, BOT_TOKEN, CREDS

from tg_bot import BotManager
from auth_web_app import auth_app
from db import DBClient


logger = logging.getLogger('GDriveSavingBotMain')


async def _db_connect(application: web.Application):
    application['db_client'] = await DBClient.connect(DB_FILE_NAME)


async def _db_disconnect(application: web.Application):
    await application['db_client'].disconnect()


async def _init_google_client(application: web.Application):
    cl = Aiogoogle(client_creds=CREDS)
    application['google_client'] = Aiogoogle(client_creds=CREDS)


async def _start_tg_bot(application: web.Application):
    bot_manager = BotManager(application['db_client'], application['google_client'])
    await bot_manager.start_tg_bot()
    application['bot_manager'] = bot_manager


async def _stop_tg_bot(application: web.Application):
    await application['bot_manager'].stop_tg_bot()


if __name__ == '__main__':
    if not APP_CLIENT_ID or not APP_API_HASH or not BOT_TOKEN:
        logger.error("No telegram bot api token was given.")
        sys.exit(1)

    auth_app.on_startup.append(_db_connect)
    auth_app.on_startup.append(_init_google_client)
    auth_app.on_startup.append(_start_tg_bot)

    auth_app.on_cleanup.append(_stop_tg_bot)
    auth_app.on_cleanup.append(_db_disconnect)

    web.run_app(auth_app)
