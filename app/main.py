# 1. Create a customer
# 2. Create an identity record for the customer
# 3. Create a USD fiat account for the customer
# 4. Create a BTC-USD trading account for the customer
# 5. Generate a book transfer quote in USD
# 6. Execute the book transfer quote using a transfer
# 7. Get the balance of the customer's USD fiat account
# 8. Generate a buy quote in BTC-USD
# 9. Execute the buy quote using a trade
# 10. Get the balance of the customer's BTC-USD trading account

import logging
import secrets
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
    transfers_bank_api,
)
from cybrid_api_bank.model.post_account import PostAccount
from cybrid_api_bank.model.post_customer import PostCustomer
from cybrid_api_bank.model.post_identity_record import PostIdentityRecord
from cybrid_api_bank.model.post_identity_record_attestation_details import (
    PostIdentityRecordAttestationDetails,
)
from cybrid_api_bank.model.post_quote import PostQuote
from cybrid_api_bank.model.post_trade import PostTrade
from cybrid_api_bank.model.post_transfer import PostTransfer
from cybrid_api_bank.model.post_one_time_address import PostOneTimeAddress

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
    configuration = cybrid_api_bank.Configuration(
        access_token=token,
        host=f"https://bank.{Config.BASE_URL}",
    )

    return configuration


def create_api_client():
    token = get_token()
    configuration = create_configuration(token)
    return cybrid_api_bank.ApiClient(configuration)


def get_verification_keys(api_client):
    logger.info("Getting verification keys...")

    api_instance = verification_keys_bank_api.VerificationKeysBankApi(api_client)

    try:
        api_response = api_instance.list_verification_keys()
        logger.info("Got verification keys.")
        return api_response
    except cybrid_api_bank.ApiException as e:
        logger.error(f"An API error occurred when getting verification keys: {e}")
        raise e
    except Exception as e:
        logger.error(f"An unknown error occurred when getting verification keys: {e}")
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


def create_account(api_client, customer, account_type, asset):
    logger.info(f"Creating {account_type} account for asset {asset}...")

    api_instance = accounts_bank_api.AccountsBankApi(api_client)
    post_account = PostAccount(
        type=account_type,
        customer_guid=customer.guid,
        asset=asset,
        name=f"{asset} account for {customer.guid}",
    )

    try:
        api_response = api_instance.create_account(post_account)
        logger.info(f"Created {account_type} account.")
        return api_response
    except cybrid_api_bank.ApiException as e:
        logger.error(f"An API error occurred when creating account: {e}")
        raise e
    except Exception as e:
        logger.error(f"An unknown error occurred when creating account: {e}")
        raise e


def get_account(api_client, guid):
    logger.info("Getting account...")

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


def wait_for_account_created(api_client, account):
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


def create_quote(
    api_client, customer, product_type, side, receive_amount, symbol=None, asset=None
):
    if symbol is not None:
        logger.info(
            f"Creating {side} {product_type} quote for {symbol} of {receive_amount}"
        )
    if asset is not None:
        logger.info(
            f"Creating {side} {product_type} quote for {asset} of {receive_amount}"
        )

    kwargs = {
        "product_type": product_type,
        "customer_guid": customer.guid,
        "side": side,
        "receive_amount": receive_amount,
    }

    if symbol is not None:
        kwargs["symbol"] = symbol
    if asset is not None:
        kwargs["asset"] = asset

    api_instance = quotes_bank_api.QuotesBankApi(api_client)
    post_quote = PostQuote(**kwargs)

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


def create_transfer(api_client, quote, transfer_type, one_time_address=None):
    logger.info(f"Creating {transfer_type} transfer...")

    api_instance = transfers_bank_api.TransfersBankApi(api_client)

    transfer_params = {
        "quote_guid": quote.guid,
        "transfer_type": transfer_type,
    }

    if one_time_address is not None:
        transfer_params["one_time_address"] = one_time_address

    post_transfer = PostTransfer(**transfer_params)

    try:
        api_response = api_instance.create_transfer(post_transfer)
        logger.info("Created transfer.")
        return api_response
    except cybrid_api_bank.ApiException as e:
        logger.error(f"An API error occurred when creating transfer: {e}")
        raise e
    except Exception as e:
        logger.error(f"An unknown error occurred when creating transfer: {e}")
        raise e


def get_transfer(api_client, guid):
    logger.info("Getting transfer...")

    api_instance = transfers_bank_api.TransfersBankApi(api_client)

    try:
        api_response = api_instance.get_transfer(guid)
        logger.info("Got transfer")
        return api_response
    except cybrid_api_bank.ApiException as e:
        logger.error(f"An API error occurred when getting transfer: {e}")
        raise e
    except Exception as e:
        logger.error(f"An unknown error occurred when getting transfer: {e}")
        raise e


def wait_for_transfer_created(api_client, transfer):
    sleep_count = 0
    transfer_state = transfer.state
    final_states = [STATE_COMPLETED]
    while transfer_state not in final_states and sleep_count < Config.TIMEOUT:
        time.sleep(1)
        sleep_count += 1
        transfer = get_transfer(api_client, transfer.guid)
        transfer_state = transfer.state
    if transfer_state != STATE_COMPLETED:
        raise BadResultError(f"Transfer has invalid state: {transfer_state}")

    logger.info(f"Transfer successfully completed with state {transfer_state}")


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


def wait_for_trade_created(api_client, trade):
    sleep_count = 0
    trade_state = trade.state
    final_states = [STATE_SETTLING]
    while trade_state not in final_states and sleep_count < Config.TIMEOUT:
        time.sleep(1)
        sleep_count += 1
        trade = get_trade(api_client, trade.guid)
        trade_state = trade.state
    if trade_state != STATE_SETTLING:
        raise BadResultError(f"Trade has invalid state: {trade_state}")

    logger.info(f"Trade successfully completed with state {trade_state}")


def main():
    create_logging_handler()
    api_client = create_api_client()

    verification_key = get_verification_keys(api_client).objects[0]
    verification_key_state = verification_key.state
    if verification_key_state != STATE_VERIFIED:
        raise BadResultError(
            f"Verification key has invalid state: #{verification_key_state}"
        )

    #
    # Create customer
    #

    customer = create_customer(api_client)

    #
    # Upload identity record
    #

    attestation_signing_key = load_pem_private_key(
        str.encode(Config.ATTESTATION_SIGNING_KEY), None
    )
    identity_record = create_identity(
        api_client, attestation_signing_key, verification_key, customer
    )

    sleep_count = 0
    identity_record_state = identity_record.attestation_details.state
    final_states = [STATE_VERIFIED, STATE_FAILED]
    while identity_record_state not in final_states and sleep_count < Config.TIMEOUT:
        time.sleep(1)
        sleep_count += 1
        identity_record = get_identity(api_client, identity_record.guid)
        identity_record_state = identity_record.attestation_details.state
    if identity_record_state != STATE_VERIFIED:
        raise BadResultError(
            f"Identity record has invalid state: {identity_record_state}"
        )

    logger.info(
        f"Identity record successfully created with state {identity_record_state}"
    )

    #
    # Create accounts
    #

    # Fiat USD account

    fiat_usd_account = create_account(api_client, customer, "fiat", "USD")
    wait_for_account_created(api_client, fiat_usd_account)

    # Crypto BTC account

    crypto_btc_account = create_account(api_client, customer, "trading", "BTC")
    wait_for_account_created(api_client, crypto_btc_account)

    #
    # Add funds to account
    #

    usd_quantity = 1 * int(1e5)
    fiat_book_transfer_quote = create_quote(
        api_client, customer, "book_transfer", "deposit", usd_quantity, asset="USD"
    )
    transfer = create_transfer(api_client, fiat_book_transfer_quote, "book")

    wait_for_transfer_created(api_client, transfer)

    #
    # Check USD balance
    #

    fiat_usd_account = get_account(api_client, fiat_usd_account.guid)
    fiat_balance = fiat_usd_account.platform_balance
    if fiat_balance != usd_quantity:
        raise BadResultError(
            f"Account has an unexpected balance: {fiat_balance}. Should be {usd_quantity}"
        )

    logger.info(f"Account has the expected balance: {fiat_balance}")

    #
    # Purchase BTC
    #

    btc_quantity = 1 * int(1e5)
    crypto_trading_btc_quote = create_quote(
        api_client, customer, "trading", "buy", btc_quantity, symbol="BTC-USD"
    )
    trade = create_trade(api_client, crypto_trading_btc_quote)

    wait_for_trade_created(api_client, trade)

    #
    # Check BTC balance
    #

    crypto_btc_account = get_account(api_client, crypto_btc_account.guid)
    crypto_balance = crypto_btc_account.platform_balance
    if crypto_balance != btc_quantity:
        raise BadResultError(
            f"Account has an unexpected balance: {crypto_balance}. Should be {btc_quantity}"
        )

    logger.info(f"Account has the expected balance: {crypto_balance}")

    #
    # Transfer BTC
    #

    btc_withdrawal_quantity = 5 * int(1e4)
    crypto_withdrawal_btc_quote = create_quote(
        api_client,
        customer,
        "crypto_transfer",
        "withdrawal",
        btc_withdrawal_quantity,
        asset="BTC",
    )
    crypto_transfer = create_transfer(
        api_client,
        crypto_withdrawal_btc_quote,
        "crypto",
        PostOneTimeAddress(
            address=secrets.token_hex(16),
            tag=None,
        ),
    )

    wait_for_transfer_created(api_client, crypto_transfer)

    #
    # Check BTC balance
    #

    crypto_btc_account = get_account(api_client, crypto_btc_account.guid)
    crypto_balance = crypto_btc_account.platform_balance
    if crypto_balance != (btc_quantity - btc_withdrawal_quantity):
        raise BadResultError(
            f"Account has an unexpected balance: {crypto_balance}. Should be {btc_quantity - btc_withdrawal_quantity}"
        )

    logger.info(f"Account has the expected balance: {crypto_balance}")
    logger.info("Test has completed successfully!")


if __name__ == "__main__":
    main()
