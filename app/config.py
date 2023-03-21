import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    BANK_GUID = os.getenv("BANK_GUID")
    BASE_URL = os.getenv("BASE_URL")
    URL_SCHEME = os.getenv("URL_SCHEME", default="https")
    CLIENT_ID = os.getenv("APPLICATION_CLIENT_ID")
    CLIENT_SECRET = os.getenv("APPLICATION_CLIENT_SECRET")
    TIMEOUT = int(os.getenv("TIMEOUT", default=30))
