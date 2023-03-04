import time
import json
import logging
import asyncio
import traceback

from aiogoogle.auth.utils import create_secret

from settings import G_APP_CREDS
from .drive import GoogleDrive

_logger = logging.getLogger(__name__)


class GoogleSession:
    def __init__(self, google_client, db_client, user_id):
        self._db_client = db_client
        self._google_client = google_client

        self._user_id = user_id
        self._user_creds = None
        self._drive_client = None

    def __await__(self):
        yield from self._authenticate_user().__await__()
        return self

    @property
    def drive(self):
        return self._drive_client

    async def _update_user_creds(self, new_creds: dict):
        self._user_creds = new_creds
        self._drive_client = GoogleDrive(self._google_client, self._user_creds)

    async def _authenticate_user(self):
        print("Authentication")
        if (user_creds := await self._db_client.get_user_creds(self._user_id)) is not None:
            if self._google_client.oauth2.is_expired(user_creds):
                try:
                    user_creds = await self._google_client.oauth2.refresh(user_creds)
                    await self._db_client.save_user_creds(json.dumps(user_creds), user_id=self._user_id)
                except Exception:
                    _logger.error(traceback.format_exc())
                    await self._db_client.delete_auth(self._user_id)
                else:
                    await self._update_user_creds(user_creds)
            else:
                await self._update_user_creds(user_creds)
        else:
            self._user_creds = None

    def is_authorized(self) -> bool:
        return self._user_creds is not None

    async def wait_for_authorization(self, timeout: float = 120.0):
        start_time = time.time()

        while True:
            if (user_creds := await self._db_client.get_user_creds(self._user_id)) is not None:
                await self._update_user_creds(user_creds)
                break

            if time.time() - start_time >= timeout:
                await self._db_client.delete_auth(self._user_id)
                break

            await asyncio.sleep(5.0)

    async def get_authorization_url(self) -> str:
        secret = create_secret()
        await self._db_client.init_auth(self._user_id, secret)

        return self._google_client.oauth2.authorization_url(
            client_creds=G_APP_CREDS,
            state=secret,
            access_type="offline",
            include_granted_scopes=True,
            prompt="select_account consent",
        )
