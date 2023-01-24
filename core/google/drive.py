from typing import Union

from aiogoogle.auth.creds import UserCreds
from aiogoogle.excs import HTTPError


class GDriveClient:
    _FOLDER_MIME_TYPE = 'application/vnd.google-apps.folder'

    def __init__(self, google_client, db_client):
        self._google_client = google_client
        self._db_client = db_client

    async def upload_file(self, file, user_creds, parent_folder_id=None):
        async with self._google_client as google:
            drive_v3 = await google.discover('drive', 'v3')

            metadata = {
                'name': file.name,
                'mimeType': file.mime_type
            }

            if parent_folder_id is not None:
                metadata['parents'] = [parent_folder_id]

            upload_request = drive_v3.files.create(
                pipe_from=file,
                json=metadata,
                fields='id,name,webContentLink,webViewLink'
            )

            return await google.as_user(upload_request, user_creds=UserCreds(**user_creds))

    async def make_file_public(self, file_id, user_creds) -> bool:
        async with self._google_client as google:
            drive_v3 = await google.discover('drive', 'v3')
            update_request = drive_v3.permissions.create(
                fileId=file_id,
                json={'type': 'anyone', 'role': 'reader'}
            )
            try:
                await google.as_user(update_request, user_creds=user_creds)
            except HTTPError:
                return False
            else:
                return True

    async def get_folder_id(self, folder_name: str, user_creds) -> str:
        async with self._google_client as google:
            drive = await google.discover('drive', 'v3')
            request = drive.files.list(q=f"mimeType='{self._FOLDER_MIME_TYPE}' and name='{folder_name}'")
            found_folders = await google.as_user(request, user_creds=UserCreds(**user_creds))

        if found_folders := found_folders['files']:
            return found_folders[0]['id']

    async def create_folder(self, folder_name: str, user_creds, parent_folder=None) -> Union[str, None]:
        async with self._google_client as google:
            drive = await google.discover('drive', 'v3')

            metadata = {
                'name': folder_name,
                'mimeType': self._FOLDER_MIME_TYPE
            }
            if parent_folder is not None:
                metadata['parents'] = [parent_folder]

            request = drive.files.create(json=metadata)

            try:
                result = await google.as_user(request, user_creds=UserCreds(**user_creds))
            except HTTPError:
                return None
            else:
                return result.get('id')
