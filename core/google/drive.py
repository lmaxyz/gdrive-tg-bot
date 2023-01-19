


class GDriveClient:
    def __init__(self, google_client, db_client):
        self._google_client = google_client
        self._db_client = db_client

    async def save_file(self, file_name, mime_type, content):
        pass
