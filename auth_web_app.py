import json

from aiogoogle.excs import HTTPError
from aiohttp import web

from settings import GAPP_CREDS, BOT_URL


async def handle_auth(request: web.Request):
    db_client = request.app.get('db_client')
    google_client = request.app.get('google_client')

    if (code := request.query.get("code")) and (secret := request.query.get('state')):

        if await db_client.get_secret(secret) is not None:
            try:
                user_creds = await google_client.oauth2.build_user_creds(grant=code, client_creds=GAPP_CREDS)
            except HTTPError as e:
                return web.Response(text=str(e))
            else:
                await db_client.save_user_creds(secret, json.dumps(user_creds))
                raise web.HTTPFound(BOT_URL)

    return web.Response(text="Something went wrong.")

auth_callback_path = '/'

try:
    auth_callback_path += GAPP_CREDS['redirect_uri'].split('/', 3)[3]
except IndexError:
    pass


auth_app = web.Application()
auth_app.add_routes([web.get(auth_callback_path, handle_auth)])
