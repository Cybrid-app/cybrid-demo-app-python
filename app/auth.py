from config import Config
import requests

AUTH_URL = f"{Config.URL_SCHEME}://id.{Config.BASE_URL}/oauth/token"

ACCOUNTS_SCOPES = ["accounts:read", "accounts:execute"]
BANKS_SCOPES = ["banks:read", "banks:write"]
CUSTOMER_SCOPES = [
    "customers:read",
    "customers:write",
    "customers:execute",
]
PRICES_SCOPES = ["prices:read"]
QUOTES_SCOPES = ["quotes:read", "quotes:execute"]
TRADES_SCOPES = ["trades:read", "trades:execute"]
TRANSFERS_SCOPES = ["transfers:read", "transfers:execute"]
EXTERNAL_WALLET_SCOPES = ["external_wallets:read", "external_wallets:execute"]
SCOPES = [
    *ACCOUNTS_SCOPES,
    *BANKS_SCOPES,
    *CUSTOMER_SCOPES,
    *PRICES_SCOPES,
    *QUOTES_SCOPES,
    *TRADES_SCOPES,
    *TRANSFERS_SCOPES,
    *EXTERNAL_WALLET_SCOPES,
]


def get_token():
    auth_headers = {"Content-type": "application/json"}
    auth_body = {
        "grant_type": "client_credentials",
        "client_id": Config.CLIENT_ID,
        "client_secret": Config.CLIENT_SECRET,
        "scope": " ".join(SCOPES),
    }
    response = requests.post(
        AUTH_URL, headers=auth_headers, json=auth_body
    )
    token = response.json()["access_token"]
    return token
