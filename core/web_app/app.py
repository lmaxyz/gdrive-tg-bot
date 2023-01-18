import json
import logging

from aiogoogle.excs import HTTPError
from aiohttp import web

from settings import G_APP_CREDS, BOT_URL

from .startup import startup_actions
from .cleanup import cleanup_actions


_logger = logging.getLogger("GoogleAuthWebApp")


async def handle_auth(request: web.Request):
    db_client = request.app.get('db_client')
    google_client = request.app.get('google_client')

    if (code := request.query.get("code")) and (secret := request.query.get('state')):

        if await db_client.get_secret(secret) is not None:
            try:
                user_creds = await google_client.oauth2.build_user_creds(grant=code, client_creds=G_APP_CREDS)
            except HTTPError as e:
                _logger.error(str(e))
            else:
                await db_client.save_user_creds(json.dumps(user_creds), secret=secret)
                raise web.HTTPFound(BOT_URL)

    return web.Response(text="Something went wrong.")


auth_callback_path = '/'

try:
    auth_callback_path += G_APP_CREDS['redirect_uri'].split('/', 3)[3]
except IndexError:
    pass

auth_app = web.Application()
auth_app.add_routes([web.get(auth_callback_path, handle_auth)])

auth_app.on_startup.extend(startup_actions)
auth_app.on_cleanup.extend(cleanup_actions)
