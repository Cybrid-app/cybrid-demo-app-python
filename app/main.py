# 1. Create a customer
# 2. Create an attested identity verification for the customer
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
from datetime import date

import cybrid_api_bank
from cybrid_api_bank.apis import (
    AccountsBankApi,
    CustomersBankApi,
    IdentityVerificationsBankApi,
    QuotesBankApi,
    TradesBankApi,
    TransfersBankApi,
)
from cybrid_api_bank.models import (
    PostAccount,
    PostCustomer, 
    PostCustomerName, 
    PostCustomerAddress, 
    PostIdentificationNumber,
    PostIdentityVerification,
    PostIdentityVerificationAddress,
    PostIdentityVerificationName,
    PostQuote,
    PostTrade,
    PostTransfer,
    PostOneTimeAddress
)

from auth import get_token
from config import Config


class ScriptError(Exception):
    pass


class BadResultError(ScriptError):
    pass


STATE_CREATED = "created"
STATE_COMPLETED = "completed"
STATE_SETTLING = "settling"
STATE_UNVERIFIED = "unverified"


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
        host=f"{Config.URL_SCHEME}://bank.{Config.BASE_URL}",
    )

    return configuration


def create_api_client():
    token = get_token()
    configuration = create_configuration(token)
    return cybrid_api_bank.ApiClient(configuration)


def create_person():
    return dict(
        name=dict(
            first="Jane",
            middle=None,
            last="Doe",
        ),
        address=dict(
            street="15310 Taylor Walk Suite 995",
            street2=None,
            city="New York",
            subdivision="NY",
            postal_code="12099",
            country_code="US",
        ),
        date_of_birth="2001-01-01",
        email_address="jane.doe@example.org",
        phone_number="+12406525665",
        identification_numbers=[
            dict(
                type="social_security_number",
                issuing_country_code="US",
                identification_number="669-55-0349",
            ),
        ],
    )


def create_customer(api_client, person):
    logger.info("Creating customer...")

    api_instance = CustomersBankApi(api_client)
    post_customer = PostCustomer(
        type="individual",
        name=PostCustomerName(**person["name"]),
        address=PostCustomerAddress(**person["address"]),
        date_of_birth=date.fromisoformat(person["date_of_birth"]),
        email_address=person["email_address"],
        phone_number=person["phone_number"],
        identification_numbers=[
            PostIdentificationNumber(**x) for x in person["identification_numbers"]
        ],
    )

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


def get_customer(api_client, guid):
    logger.info("Getting customer...")

    api_instance = CustomersBankApi(api_client)

    try:
        api_response = api_instance.get_customer(guid)
        logger.info("Got customer.")
        return api_response
    except cybrid_api_bank.ApiException as e:
        logger.error(f"An API error occurred when getting customer: {e}")
        raise e
    except Exception as e:
        logger.error(f"An unknown error occurred when getting customer: {e}")
        raise e


def wait_for_customer_unverified(api_client, customer):
    sleep_count = 0
    customer_state = customer.state
    final_states = [STATE_UNVERIFIED]
    while customer_state not in final_states and sleep_count < Config.TIMEOUT:
        time.sleep(1)
        sleep_count += 1
        customer = get_customer(api_client, customer.guid)
        customer_state = customer.state
    if customer_state not in final_states:
        raise BadResultError(f"Customer has invalid state: {customer_state}")

    logger.info(f"Customer successfully created with state {customer_state}")


def create_account(api_client, customer, account_type, asset):
    logger.info(f"Creating {account_type} account for asset {asset}...")

    api_instance = AccountsBankApi(api_client)
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

    api_instance = AccountsBankApi(api_client)

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
    if account_state not in final_states:
        raise BadResultError(f"Account has invalid state: {account_state}")

    logger.info(f"Account successfully created with state {account_state}")


def create_identity_verification(api_client, customer, person):
    logger.info("Creating identity verification...")

    api_instance = IdentityVerificationsBankApi(api_client)
    post_identity_verification = PostIdentityVerification(
        type="kyc",
        method="attested",
        customer_guid=customer.guid,
        name=PostIdentityVerificationName(**person["name"]),
        address=PostIdentityVerificationAddress(**person["address"]),
        date_of_birth=date.fromisoformat(person["date_of_birth"]),
        identification_numbers=[
            PostIdentificationNumber(**x) for x in person["identification_numbers"]
        ],
    )

    try:
        api_response = api_instance.create_identity_verification(post_identity_verification)
        logger.info("Created identity verification.")
        return api_response
    except cybrid_api_bank.ApiException as e:
        logger.error(f"An API error occurred when creating identity verification: {e}")
        raise e
    except Exception as e:
        logger.error(f"An unknown error occurred when creating identity verification: {e}")
        raise e


def get_identity_verification(api_client, guid):
    logger.info("Getting identity verification...")

    api_instance = IdentityVerificationsBankApi(api_client)

    try:
        api_response = api_instance.get_identity_verification(guid)
        logger.info("Got identity record.")
        return api_response
    except cybrid_api_bank.ApiException as e:
        logger.error(f"An API error occurred when getting identity verification: {e}")
        raise e
    except Exception as e:
        logger.error(f"An unknown error occurred when getting identity verification: {e}")
        raise e


def wait_for_identity_verification_completed(api_client, identity_verification):
    sleep_count = 0
    identity_verification_state = identity_verification.state
    final_states = [STATE_COMPLETED]
    while identity_verification_state not in final_states and sleep_count < Config.TIMEOUT:
        time.sleep(1)
        sleep_count += 1
        identity_verification = get_identity_verification(api_client, identity_verification.guid)
        identity_verification_state = identity_verification.state
    if identity_verification_state not in final_states:
        raise BadResultError(f"Identity verification has invalid state: {identity_verification_state}")

    logger.info(f"Identity verification successfully completed with state {identity_verification_state}")


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

    api_instance = QuotesBankApi(api_client)
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

    api_instance = TransfersBankApi(api_client)

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

    api_instance = TransfersBankApi(api_client)

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


def wait_for_transfer_completed(api_client, transfer):
    sleep_count = 0
    transfer_state = transfer.state
    final_states = [STATE_COMPLETED]
    while transfer_state not in final_states and sleep_count < Config.TIMEOUT:
        time.sleep(1)
        sleep_count += 1
        transfer = get_transfer(api_client, transfer.guid)
        transfer_state = transfer.state
    if transfer_state not in final_states:
        raise BadResultError(f"Transfer has invalid state: {transfer_state}")

    logger.info(f"Transfer successfully completed with state {transfer_state}")


def create_trade(api_client, quote):
    logger.info("Creating trade...")

    api_instance = TradesBankApi(api_client)
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

    api_instance = TradesBankApi(api_client)

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


def wait_for_trade_completed(api_client, trade):
    sleep_count = 0
    trade_state = trade.state
    final_states = [STATE_SETTLING]
    while trade_state not in final_states and sleep_count < Config.TIMEOUT:
        time.sleep(1)
        sleep_count += 1
        trade = get_trade(api_client, trade.guid)
        trade_state = trade.state
    if trade_state not in final_states:
        raise BadResultError(f"Trade has invalid state: {trade_state}")

    logger.info(f"Trade successfully completed with state {trade_state}")


def main():
    create_logging_handler()
    person = create_person()
    api_client = create_api_client()

    #
    # Create customer
    #

    customer = create_customer(api_client, person)
    wait_for_customer_unverified(api_client, customer)

    #
    # Create identity verification
    #

    identity_verification = create_identity_verification(api_client, customer, person)
    wait_for_identity_verification_completed(api_client, identity_verification)

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

    usd_quantity = 100_000
    fiat_book_transfer_quote = create_quote(
        api_client, customer, "book_transfer", "deposit", usd_quantity, asset="USD"
    )
    transfer = create_transfer(api_client, fiat_book_transfer_quote, "book")

    wait_for_transfer_completed(api_client, transfer)

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

    btc_quantity = 100_000
    crypto_trading_btc_quote = create_quote(
        api_client, customer, "trading", "buy", btc_quantity, symbol="BTC-USD"
    )
    trade = create_trade(api_client, crypto_trading_btc_quote)

    wait_for_trade_completed(api_client, trade)

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

    btc_withdrawal_quantity = 50_000
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

    wait_for_transfer_completed(api_client, crypto_transfer)

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
