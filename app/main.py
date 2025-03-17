# 1. Create a customer
# 2. Create a passed immediately identity verification for the customer
# 3. Get USD fiat account for the bank
# 4. Create a USD fiat accuont for the customer
# 5. Generate a book transfer quote in USD
# 6. Execute the book transfer quote using a transfer
# 7. Get the balance of the customer's USD fiat account
# 8. Create a crypto trading accounts: BTC, ETH, USDC for the customer
# 9. Create cyrpto wallets for the customer
# 10. Generate buy quotes
# 11. Execute buy quotes using a trade
# 12. Execute a crypto withdrawal
# 13. Get the balance of the customer's crypto trading account

import logging
import secrets
import sys
import time
from datetime import date

import cybrid_api_bank
from cybrid_api_bank.apis import (
    AccountsBankApi,
    BanksBankApi,
    CustomersBankApi,
    IdentityVerificationsBankApi,
    QuotesBankApi,
    TradesBankApi,
    TransfersBankApi,
    ExternalWalletsBankApi,
)
from cybrid_api_bank.models import (
    Bank,
    PostAccount,
    PostCustomer,
    PostIdentityVerification,
    PostQuote,
    PostTrade,
    PostTransfer,
    PostTransferParticipant,
    PostCustomerAddress,
    PostCustomerName,
    PostIdentificationNumber,
    PostIdentityVerificationAddress,
    PostIdentityVerificationName,
    PostExternalWallet,
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

IDENTITY_VERIFICATION_EXPECTED_BEHAVIOUR_PASSED_IMMEDIATELY = "passed_immediately"


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


def get_bank(api_client):
    logger.info("Getting bank...")

    api_instance = BanksBankApi(api_client)

    # https://docs.cybrid.xyz/reference/getbank
    return api_instance.get_bank(bank_guid=Config.BANK_GUID)


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
            dict(
                type="drivers_license",
                issuing_country_code="US",
                identification_number="D152096714850065",
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
        # https://docs.cybrid.xyz/reference/createcustomer
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
        # https://docs.cybrid.xyz/reference/getcustomer
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
        # https://docs.cybrid.xyz/reference/createaccount
        api_response = api_instance.create_account(post_account)
        logger.info(f"Created {account_type} account.")
        return api_response
    except cybrid_api_bank.ApiException as e:
        logger.error(f"An API error occurred when creating account: {e}")
        raise e
    except Exception as e:
        logger.error(f"An unknown error occurred when creating account: {e}")
        raise e


def list_accounts(api_client, owner, type):
    logger.info("Listing accounts...")

    api_instance = AccountsBankApi(api_client)

    try:
        # https://docs.cybrid.xyz/reference/listaccounts
        accounts = api_instance.list_accounts(owner=owner, type=type)

        logger.info("Got accounts.")

        return accounts.objects
    except cybrid_api_bank.ApiException as e:
        logger.error(f"An API error occurred when listing accounts: {e}")
        raise e
    except Exception as e:
        logger.error(f"An unknown error occurred when listing accounts: {e}")
        raise e


def get_account(api_client, guid):
    logger.info("Getting account...")

    api_instance = AccountsBankApi(api_client)

    try:
        # https://docs.cybrid.xyz/reference/getaccount
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
        method="id_and_selfie",
        customer_guid=customer.guid,
        name=PostIdentityVerificationName(**person["name"]),
        address=PostIdentityVerificationAddress(**person["address"]),
        date_of_birth=date.fromisoformat(person["date_of_birth"]),
        identification_numbers=[
            PostIdentificationNumber(**x) for x in person["identification_numbers"]
        ],
        expected_behaviours=[
            IDENTITY_VERIFICATION_EXPECTED_BEHAVIOUR_PASSED_IMMEDIATELY
        ],
    )

    try:
        # https://docs.cybrid.xyz/reference/createidentityverification
        api_response = api_instance.create_identity_verification(
            post_identity_verification
        )
        logger.info("Created identity verification.")
        return api_response
    except cybrid_api_bank.ApiException as e:
        logger.error(f"An API error occurred when creating identity verification: {e}")
        raise e
    except Exception as e:
        logger.error(
            f"An unknown error occurred when creating identity verification: {e}"
        )
        raise e


def get_identity_verification(api_client, guid):
    logger.info("Getting identity verification...")

    api_instance = IdentityVerificationsBankApi(api_client)

    try:
        # https://docs.cybrid.xyz/reference/getidentityverification
        api_response = api_instance.get_identity_verification(guid)
        logger.info("Got identity record.")
        return api_response
    except cybrid_api_bank.ApiException as e:
        logger.error(f"An API error occurred when getting identity verification: {e}")
        raise e
    except Exception as e:
        logger.error(
            f"An unknown error occurred when getting identity verification: {e}"
        )
        raise e


def wait_for_identity_verification_completed(api_client, identity_verification):
    sleep_count = 0
    identity_verification_state = identity_verification.state
    final_states = [STATE_COMPLETED]
    while (
        identity_verification_state not in final_states and sleep_count < Config.TIMEOUT
    ):
        time.sleep(1)
        sleep_count += 1
        identity_verification = get_identity_verification(
            api_client, identity_verification.guid
        )
        identity_verification_state = identity_verification.state
    if identity_verification_state not in final_states:
        raise BadResultError(
            f"Identity verification has invalid state: {identity_verification_state}"
        )

    logger.info(
        f"Identity verification successfully completed with state {identity_verification_state}"
    )


def create_quote(
    api_client,
    customer,
    product_type,
    side,
    deliver_amount=None,
    receive_amount=None,
    symbol=None,
    asset=None,
):
    if deliver_amount is not None:
        amount = deliver_amount
    if receive_amount is not None:
        amount = receive_amount

    if symbol is not None:
        logger.info(f"Creating {side} {product_type} quote for {symbol} of {amount}")
    if asset is not None:
        logger.info(f"Creating {side} {product_type} quote for {asset} of {amount}")

    kwargs = {
        "product_type": product_type,
        "customer_guid": customer.guid,
        "side": side,
    }

    if symbol is not None:
        kwargs["symbol"] = symbol
    if asset is not None:
        kwargs["asset"] = asset
    if deliver_amount is not None:
        kwargs["deliver_amount"] = deliver_amount
    if receive_amount is not None:
        kwargs["receive_amount"] = receive_amount

    api_instance = QuotesBankApi(api_client)
    post_quote = PostQuote(**kwargs)

    try:
        # https://docs.cybrid.xyz/reference/createquote
        api_response = api_instance.create_quote(post_quote)
        logger.info("Created quote.")
        return api_response
    except cybrid_api_bank.ApiException as e:
        logger.error(f"An API error occurred when creating quote: {e}")
        raise e
    except Exception as e:
        logger.error(f"An unknown error occurred when creating quote: {e}")
        raise e


def create_transfer(
    api_client,
    quote,
    transfer_type,
    source_platform_account=None,
    destination_platform_account=None,
    external_wallet=None,
    source_participant=None,
    destination_participant=None,
):
    logger.info(f"Creating {transfer_type} transfer...")

    api_instance = TransfersBankApi(api_client)

    transfer_params = {
        "quote_guid": quote.guid,
        "transfer_type": transfer_type,
    }

    if source_platform_account is not None:
        transfer_params["source_account_guid"] = source_platform_account.guid
    if destination_platform_account is not None:
        transfer_params["destination_account_guid"] = destination_platform_account.guid
    if external_wallet is not None:
        transfer_params["external_wallet_guid"] = external_wallet.guid
    if source_participant is not None:
        if isinstance(source_participant, Bank):
            type = "bank"
        else:
            type = "customer"

        transfer_params["source_participants"] = [
            PostTransferParticipant(
                type=type,
                amount=quote.deliver_amount,
                guid=source_participant.guid,
            )
        ]
    if destination_participant is not None:
        if isinstance(destination_participant, Bank):
            type = "bank"
        else:
            type = "customer"

        transfer_params["destination_participants"] = [
            PostTransferParticipant(
                type=type,
                amount=quote.receive_amount,
                guid=destination_participant.guid,
            )
        ]

    post_transfer = PostTransfer(**transfer_params)

    try:
        # https://docs.cybrid.xyz/reference/createtransfer
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
        # https://docs.cybrid.xyz/reference/gettransfer
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
        # https://docs.cybrid.xyz/reference/createtrade
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
        # https://docs.cybrid.xyz/reference/gettrade
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


def wait_for_expected_account_balance(api_client, platform_account, expected_balance):
    sleep_count = 0
    account = get_account(api_client, platform_account.guid)
    platform_balance = account.platform_balance

    while platform_balance != expected_balance and sleep_count < Config.TIMEOUT:
        time.sleep(1)
        sleep_count += 1
        account = get_account(api_client, platform_account.guid)
        platform_balance = account.platform_balance

    if platform_balance != expected_balance:
        raise BadResultError(f"Account has an unexpected balance: {platform_balance}.")

    logger.info("Expected account balance successfully found.")


def create_external_wallet(api_client, customer, asset):
    logger.info(f"Creating external wallet for {asset}...")

    api_instance = ExternalWalletsBankApi(api_client)

    body = PostExternalWallet(
        name=f"External wallet for {customer.guid}",
        asset=asset,
        address=secrets.token_hex(16),
        tag=secrets.token_hex(16),
        customer_guid=customer.guid,
    )

    try:
        # https://docs.cybrid.xyz/reference/createexternalwallet
        external_wallet = api_instance.create_external_wallet(post_external_wallet=body)
        logger.info("Created external wallet.")
        return external_wallet
    except cybrid_api_bank.ApiException as e:
        logger.error(f"An API error occurred when creating an external wallet: {e}")
        raise e
    except Exception as e:
        logger.error(f"An unknown error occurred when creating external wallet: {e}")
        raise e


def get_external_wallet(api_client, guid):
    logger.info("Getting external wallet...")

    api_instance = ExternalWalletsBankApi(api_client)

    try:
        # https://docs.cybrid.xyz/reference/getexternalwallet
        external_wallet = api_instance.get_external_wallet(guid)
        logger.info("Got external wallet")
        return external_wallet
    except cybrid_api_bank.ApiException as e:
        logger.error(f"An API error occurred when getting external wallet: {e}")
        raise e
    except Exception as e:
        logger.error(f"An unknown error occurred when getting external wallet: {e}")
        raise e


def wait_for_external_wallet_completed(api_client, external_wallet):
    sleep_count = 0
    external_wallet_state = external_wallet.state
    final_states = [STATE_COMPLETED]
    while external_wallet_state not in final_states and sleep_count < Config.TIMEOUT:
        time.sleep(1)
        sleep_count += 1
        external_wallet = get_external_wallet(api_client, external_wallet.guid)
        external_wallet_state = external_wallet.state
    if external_wallet_state not in final_states:
        raise BadResultError(
            f"External wallet has invalid state: {external_wallet_state}"
        )

    logger.info(f"Trade successfully completed with state {external_wallet_state}")


def main():
    create_logging_handler()
    person = create_person()
    api_client = create_api_client()

    #
    # Get a handle to the bank
    #

    bank = get_bank(api_client)

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
    # Get bank fiat USD account
    #

    bank_accounts = list_accounts(api_client, "bank", "fiat")
    bank_fiat_usd_account = next(
        filter(lambda x: x.asset == "USD", bank_accounts), None
    )
    if not bank_fiat_usd_account:
        raise BadResultError("Bank has no USD fiat bank account")

    #
    # Create customer fiat USD account
    #

    customer_fiat_usd_account = create_account(api_client, customer, "fiat", "USD")
    wait_for_account_created(api_client, customer_fiat_usd_account)

    #
    # Add funds to account
    #

    usd_quantity = 100_000
    fiat_book_transfer_quote = create_quote(
        api_client, customer, "book_transfer", "deposit", usd_quantity, asset="USD"
    )
    transfer = create_transfer(
        api_client,
        fiat_book_transfer_quote,
        "book",
        source_platform_account=bank_fiat_usd_account,
        destination_platform_account=customer_fiat_usd_account,
        source_participant=bank,
        destination_participant=customer,
    )

    wait_for_transfer_completed(api_client, transfer)

    #
    # Check USD balance
    #

    customer_fiat_usd_account = get_account(api_client, customer_fiat_usd_account.guid)
    fiat_balance = customer_fiat_usd_account.platform_balance
    if fiat_balance != usd_quantity:
        raise BadResultError(
            f"Account has an unexpected balance: {fiat_balance}. Should be {usd_quantity}"
        )

    logger.info(f"Account has the expected balance: {fiat_balance}")

    for asset in Config.CRYPTO_ASSETS:
        crypto_accounts = {}
        crypto_wallets = {}

        #
        # Crypto accounts
        #

        crypto_accounts[asset] = create_account(api_client, customer, "trading", asset)
        wait_for_account_created(api_client, crypto_accounts[asset])

        #
        # Crypto wallets

        crypto_wallets[asset] = create_external_wallet(api_client, customer, asset)
        wait_for_external_wallet_completed(api_client, crypto_wallets[asset])

        #
        # Purchase crypto

        deliver_amount = 10_000

        quote = create_quote(
            api_client,
            customer,
            "trading",
            "buy",
            deliver_amount=deliver_amount,
            symbol=f"{asset}-USD",
        )
        trade = create_trade(api_client, quote)

        wait_for_trade_completed(api_client, trade)

        #
        # Transfer crypto

        wait_for_expected_account_balance(
            api_client, crypto_accounts[asset], trade.receive_amount
        )

        crypto_account = get_account(api_client, crypto_accounts[asset].guid)
        crypto_balance = crypto_account.platform_balance

        external_wallet = get_external_wallet(api_client, crypto_wallets[asset].guid)

        quote = create_quote(
            api_client,
            customer,
            "crypto_transfer",
            "withdrawal",
            deliver_amount=crypto_balance,
            asset=asset,
        )
        transfer = create_transfer(
            api_client,
            quote,
            "crypto",
            external_wallet=external_wallet,
            source_participant=customer,
            destination_participant=customer,
        )

        wait_for_transfer_completed(api_client, transfer)

        #
        # Check crypto balances

        wait_for_expected_account_balance(api_client, crypto_accounts[asset], 0)

        crypto_account = get_account(api_client, crypto_accounts[asset].guid)
        crypto_balance = crypto_account.platform_balance

        logger.info(
            f"Crypto {asset} account has the expected balance: {crypto_balance}"
        )

    logger.info("Test has completed successfully!")


if __name__ == "__main__":
    main()
