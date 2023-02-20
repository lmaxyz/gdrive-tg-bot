import json
import logging
import time
import asyncio
import traceback

from aiogoogle.auth.utils import create_secret

from settings import G_APP_CREDS

from core.exceptions import AuthorizationTimeout

_logger = logging.getLogger(__name__)


class GoogleAuthenticator:
    def __init__(self, bot_manager, db_client, google_client):
        self._bot_manager = bot_manager
        self._google_client = google_client
        self._db_client = db_client

    async def authenticate_user(self, user_id) -> dict:
        if (user_creds := await self._db_client.get_user_creds(user_id)) is not None:
            if self._google_client.oauth2.is_expired(user_creds):
                try:
                    user_creds = await self._google_client.oauth2.refresh(user_creds)
                    await self._db_client.save_user_creds(json.dumps(user_creds), user_id=user_id)
                except Exception:
                    _logger.error(traceback.format_exc())
                    await self._db_client.delete_auth(user_id)
                else:
                    return user_creds
            else:
                return user_creds

        return None

    async def start_authorization(self, user_id) -> dict:
        await self._init_authorization(user_id)

        try:
            return await self._wait_for_authorization(user_id)
        except AuthorizationTimeout:
            await self._db_client.delete_auth(user_id)
            return None

    async def _wait_for_authorization(self, user_id, timeout: float = 120.0) -> dict:
        start_time = time.time()

        while True:
            if (user_creds := await self._db_client.get_user_creds(user_id)) is not None:
                return user_creds

            if time.time() - start_time >= timeout:
                raise AuthorizationTimeout("Authorization haven't done.")

            await asyncio.sleep(5.0)

    async def _init_authorization(self, user_id):
        secret = create_secret()
        await self._db_client.init_auth(user_id, secret)

        url = self._google_client.oauth2.authorization_url(
            client_creds=G_APP_CREDS,
            state=secret,
            access_type="offline",
            include_granted_scopes=True,
            prompt="select_account%20consent",
        )
        await self._bot_manager.send_authorization_request(user_id, url)
