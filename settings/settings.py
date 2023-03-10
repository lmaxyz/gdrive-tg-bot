import os
import json
import dotenv
from pathlib import Path


BASE_DIR = Path(__file__).absolute().parent.parent

dotenv.load_dotenv(BASE_DIR / "settings" / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN")
APP_CLIENT_ID = os.getenv("APP_ID")
APP_API_HASH = os.getenv("APP_API_HASH")
BOT_URL = os.getenv("BOT_URL")

SCOPES = [
    'https://www.googleapis.com/auth/drive.file'
]

# Google app credentials
_CREDS_PATH = str(BASE_DIR / "settings" / "credentials.json")
G_APP_CREDS = json.load(open(_CREDS_PATH, "rb"))["web"]
G_APP_CREDS['scopes'] = SCOPES
G_APP_CREDS['redirect_uri'] = os.getenv("REDIRECT_URI")

DB_FILE_NAME = 'creds.db'

HELP_MESSAGE = """This bot created to interact with your google drive by telegram messages.
Just send message with attached document and it will uploaded to your google drive.

There are some commands to improve interaction experience:
/help - Show help text.
/create_folder - Create new folder inside current one.
/set_saving_folder - Change uploading destination folder (Default is google drive root).
"""
