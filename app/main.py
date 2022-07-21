# 1. Create a customer
# 2. Create a BTC-USD trading account
# 3. Create an identity record
# 4. Generate a buy quote for BTC-USD
# 5. Execute the buy quote
# 6. Get a balance of the customer's BTC-USD trading account

import logging
import sys
import time
from cryptography.hazmat.primitives.serialization import load_pem_private_key

import cybrid_api_bank
from cybrid_api_bank.api import (
    accounts_bank_api,
    customers_bank_api,
    verification_keys_bank_api,
    identity_records_bank_api,
    quotes_bank_api,
    trades_bank_api,
)
from cybrid_api_bank.model.post_account import PostAccount
from cybrid_api_bank.model.post_customer import PostCustomer
from cybrid_api_bank.model.post_identity_record import PostIdentityRecord
from cybrid_api_bank.model.post_identity_record_attestation_details import (
    PostIdentityRecordAttestationDetails,
)
from cybrid_api_bank.model.post_quote import PostQuote
from cybrid_api_bank.model.post_trade import PostTrade

from auth import get_token
from config import Config
from util import create_jwt


class ScriptError(Exception):
    pass


class BadResultError(ScriptError):
    pass


STATE_CREATED = "created"
STATE_COMPLETED = "completed"
STATE_FAILED = "failed"
STATE_SETTLING = "settling"
STATE_VERIFIED = "verified"


logger = logging.getLogger()
logger.setLevel(logging.INFO)


def create_logging_handler():
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def create_configuration(token):
    configuration = cybrid_api_bank.Configuration(access_token=token)
    return configuration


def create_api_client():
    token = get_token()
    configuration = create_configuration(token)
    return cybrid_api_bank.ApiClient(configuration)


def get_verification_key(api_client, guid):
    logger.info("Getting verification key...")

    api_instance = verification_keys_bank_api.VerificationKeysBankApi(api_client)

    try:
        api_response = api_instance.get_verification_key(verification_key_guid=guid)
        logger.info("Got verification key.")
        return api_response
    except cybrid_api_bank.ApiException as e:
        logger.error(f"An API error occurred when getting verification key: {e}")
        raise e
    except Exception as e:
        logger.error(f"An unknown error occurred when getting verification key: {e}")
        raise e


def create_customer(api_client):
    logger.info("Creating customer...")

    api_instance = customers_bank_api.CustomersBankApi(api_client)
    post_customer = PostCustomer(type="individual")

    try:
        api_response = api_instance.create_customer(post_customer)
        logger.info("Created customer.")
        return api_response
    except cybrid_api_bank.ApiException as e:
        logger.error(f"An API error occurred when creating customer: {e}")
        raise e
    except Exception as e:
        logger.error(f"An unknown error occurred when creating customer: {e}")
        raise e


def create_account(api_client, customer):
    logger.info("Creating account...")

    api_instance = accounts_bank_api.AccountsBankApi(api_client)
    post_account = PostAccount(
        type="trading", customer_guid=customer.guid, asset="BTC", name="Account"
    )

    try:
        api_response = api_instance.create_account(post_account)
        logger.info("Created account.")
        return api_response
    except cybrid_api_bank.ApiException as e:
        logger.error(f"An API error occurred when creating account: {e}")
        raise e
    except Exception as e:
        logger.error(f"An unknown error occurred when creating account: {e}")
        raise e


def get_account(api_client, guid):
    logger.info("Get account...")

    api_instance = accounts_bank_api.AccountsBankApi(api_client)

    try:
        api_response = api_instance.get_account(guid)
        logger.info("Got account.")
        return api_response
    except cybrid_api_bank.ApiException as e:
        logger.error(f"An API error occurred when getting account: {e}")
        raise e
    except Exception as e:
        logger.error(f"An unknown error occurred when getting account: {e}")
        raise e


def create_identity(api_client, rsa_signing_key, verification_key, customer):
    logger.info("Creating identity record...")

    api_instance = identity_records_bank_api.IdentityRecordsBankApi(api_client)

    token = create_jwt(rsa_signing_key, verification_key, customer, Config.BANK_GUID)
    attestation_details = PostIdentityRecordAttestationDetails(token=token)
    post_identity_record = PostIdentityRecord(
        customer_guid=customer.guid,
        type="attestation",
        attestation_details=attestation_details,
    )

    try:
        api_response = api_instance.create_identity_record(post_identity_record)
        logger.info("Created identity record.")
        return api_response
    except cybrid_api_bank.ApiException as e:
        logger.error(f"An API error occurred when creating identity record: {e}")
        raise e
    except Exception as e:
        logger.error(f"An unknown error occurred when creating identity record: {e}")
        raise e


def get_identity(api_client, guid):
    logger.info("Getting identity record...")

    api_instance = identity_records_bank_api.IdentityRecordsBankApi(api_client)

    try:
        api_response = api_instance.get_identity_record(guid)
        logger.info("Got identity record.")
        return api_response
    except cybrid_api_bank.ApiException as e:
        logger.error(f"An API error occurred when getting identity record: {e}")
        raise e
    except Exception as e:
        logger.error(f"An unknown error occurred when getting identity record: {e}")
        raise e


def create_quote(api_client, customer, side, symbol, receive_amount):
    logger.info(f"Creating {side} {symbol} quote of {receive_amount}")

    api_instance = quotes_bank_api.QuotesBankApi(api_client)
    post_quote = PostQuote(
        customer_guid=customer.guid,
        symbol=symbol,
        side=side,
        receive_amount=receive_amount,
    )

    try:
        api_response = api_instance.create_quote(post_quote)
        logger.info("Created quote.")
        return api_response
    except cybrid_api_bank.ApiException as e:
        logger.error(f"An API error occurred when creating quote: {e}")
        raise e
    except Exception as e:
        logger.error(f"An unknown error occurred when creating quote: {e}")
        raise e


def create_trade(api_client, quote):
    logger.info("Creating trade...")

    api_instance = trades_bank_api.TradesBankApi(api_client)
    post_trade = PostTrade(quote.guid)

    try:
        api_response = api_instance.create_trade(post_trade)
        logger.info("Created trade.")
        return api_response
    except cybrid_api_bank.ApiException as e:
        logger.error(f"An API error occurred when creating trade: {e}")
        raise e
    except Exception as e:
        logger.error(f"An unknown error occurred when creating trade: {e}")
        raise e


def get_trade(api_client, guid):
    logger.info("Getting trade...")

    api_instance = trades_bank_api.TradesBankApi(api_client)

    try:
        api_response = api_instance.get_trade(guid)
        logger.info("Got trade")
        return api_response
    except cybrid_api_bank.ApiException as e:
        logger.error(f"An API error occurred when getting trade: {e}")
        raise e
    except Exception as e:
        logger.error(f"An unknown error occurred when getting trade: {e}")
        raise e


def main():
    create_logging_handler()
    api_client = create_api_client()

    verification_key_guid = Config.VERIFICATION_KEY_GUID
    verification_key = get_verification_key(api_client, verification_key_guid)
    verification_key_state = verification_key.state
    if verification_key_state != STATE_VERIFIED:
        raise BadResultError(f"Verification key has invalid state: #{verification_key_state}")

    customer = create_customer(api_client)
    account = create_account(api_client, customer)

    attestation_signing_key = load_pem_private_key(
        str.encode(Config.ATTESTATION_SIGNING_KEY), None
    )
    identity_record = create_identity(
        api_client, attestation_signing_key, verification_key, customer
    )

    sleep_count = 0
    account_state = account.state
    final_states = [STATE_CREATED]
    while account_state not in final_states and sleep_count < Config.TIMEOUT:
        time.sleep(1)
        sleep_count += 1
        account = get_account(api_client, account.guid)
        account_state = account.state
    if account_state != STATE_CREATED:
        raise BadResultError(f"Account has invalid state: {account_state}")

    logger.info(f"Account successfully created with state {account_state}")

    sleep_count = 0
    identity_record_state = identity_record.attestation_details.state
    final_states = [STATE_VERIFIED, STATE_FAILED]
    while identity_record_state not in final_states and sleep_count < Config.TIMEOUT:
        time.sleep(1)
        sleep_count += 1
        identity_record = get_identity(api_client, identity_record.guid)
        identity_record_state = identity_record.attestation_details.state
    if identity_record_state != STATE_VERIFIED:
        raise BadResultError(f"Identity record has invalid state: {identity_record_state}")

    logger.info(f"Identity record successfully created with state {identity_record_state}")

    quantity = 5 * int(1e8)
    quote = create_quote(api_client, customer, "buy", "BTC-USD", quantity)
    trade = create_trade(api_client, quote)

    sleep_count = 0
    trade_state = trade.state
    final_states = [STATE_COMPLETED, STATE_FAILED, STATE_SETTLING]
    while trade_state not in final_states and sleep_count < Config.TIMEOUT:
        time.sleep(1)
        sleep_count += 1
        trade = get_trade(api_client, trade.guid)
        trade_state = trade.state
    if trade_state not in [STATE_COMPLETED, STATE_SETTLING]:
        raise BadResultError(f"Trade has invalid state: {trade_state}")

    account = get_account(api_client, account.guid)
    balance = account.platform_balance
    if balance != quantity:
        raise BadResultError(f"Account has an unexpected balance: {balance}")

    logger.info(f"Account has the expected balance: {balance}")
    logger.info("Test has completed successfully!")


if __name__ == "__main__":
    main()
