import os
import json
import dotenv

dotenv.load_dotenv()


BOT_TOKEN = os.getenv("BOT_TOKEN")
APP_CLIENT_ID = os.getenv("APP_ID")
APP_API_HASH = os.getenv("APP_API_HASH")
BOT_URL = os.getenv("BOT_URL")

SCOPES = [
    'https://www.googleapis.com/auth/drive.file'
]

# Google app credentials
GAPP_CREDS = json.load(open("credentials.json", "rb"))["web"]
GAPP_CREDS['scopes'] = SCOPES
GAPP_CREDS['redirect_uri'] = os.getenv("REDIRECT_URI")

DB_FILE_NAME = 'creds.db'
