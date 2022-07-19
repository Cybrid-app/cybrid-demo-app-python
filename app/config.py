import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    ATTESTATION_SIGNING_KEY = os.getenv("ATTESTATION_SIGNING_KEY")
    BANK_GUID = os.getenv("BANK_GUID")
    BASE_URL = os.getenv("BASE_URL")
    CLIENT_ID = os.getenv("APPLICATION_CLIENT_ID")
    CLIENT_SECRET = os.getenv("APPLICATION_CLIENT_SECRET")
    TIMEOUT = int(os.getenv("TIMEOUT", default=30))
    VERIFICATION_KEY_GUID = os.getenv("VERIFICATION_KEY_GUID")
