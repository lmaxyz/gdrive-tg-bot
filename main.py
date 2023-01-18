import sys
import logging

from aiohttp import web

from settings import APP_API_HASH, APP_CLIENT_ID, BOT_TOKEN

from core.web_app import auth_app


logger = logging.getLogger(__name__)


if __name__ == '__main__':
    if not APP_CLIENT_ID or not APP_API_HASH or not BOT_TOKEN:
        logger.error("No telegram bot api token was given.")
        sys.exit(1)

    web.run_app(auth_app, host='127.0.0.1')
