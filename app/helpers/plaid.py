import secrets
from typing import Tuple

from plaid import Environment, Configuration, ApiClient
from plaid.api import plaid_api
from plaid.model.products import Products
from plaid.model.sandbox_public_token_create_request import (
    SandboxPublicTokenCreateRequest,
)

from app.config import Config

PLAID_INSTITUTION_ID = "ins_109508"


def configure_plaid_client():
    plaid_environment = Environment.Sandbox
    plaid_client_id = Config.PLAID_CLIENT_ID
    plaid_secret = Config.PLAID_SANDBOX_SECRET

    configuration = Configuration(
        host=plaid_environment,
        api_key={"clientId": plaid_client_id, "secret": plaid_secret},
    )

    api_client = ApiClient(configuration)

    return plaid_api.PlaidApi(api_client)


def create_plaid_public_token():
    api_client = configure_plaid_client()

    request = SandboxPublicTokenCreateRequest(
        institution_id=PLAID_INSTITUTION_ID,
        initial_products=[Products("auth"), Products("identity")],
    )

    response = api_client.sandbox_public_token_create(request)

    return response.public_token


def handle_plaid_on_success() -> Tuple[str, str]:
    return create_plaid_public_token(), secrets.token_hex(16)
