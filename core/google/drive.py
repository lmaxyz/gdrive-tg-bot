from aiogoogle.auth.creds import UserCreds


class GDriveClient:
    def __init__(self, google_client, db_client):
        self._google_client = google_client
        self._db_client = db_client

    async def upload_file(self, file, file_name, mime_type, user_creds):
        async with self._google_client as google:
            drive_v3 = await google.discover('drive', 'v3')

            metadata = {
                'name': file_name,
                'mimeType': mime_type
            }

            upload_request = drive_v3.files.create(
                pipe_from=file,
                json=metadata,
                fields='id,name,webContentLink,webViewLink'
            )

            return await google.as_user(upload_request, user_creds=UserCreds(**user_creds))

    async def make_file_public(self, file_id, user_creds):
        async with self._google_client as google:
            drive_v3 = await google.discover('drive', 'v3')
            update_request = drive_v3.permissions.create(
                fileId=file_id,
                json={'type': 'anyone', 'role': 'reader'}
            )
            await google.as_user(update_request, user_creds=user_creds)
