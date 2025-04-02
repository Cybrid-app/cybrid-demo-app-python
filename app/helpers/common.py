import logging
import secrets
import sys
import time
from typing import Any

import cybrid_api_bank
from cybrid_api_bank.apis import (
    CounterpartiesBankApi,
    AccountsBankApi,
    BanksBankApi,
    CustomersBankApi,
    IdentityVerificationsBankApi,
    QuotesBankApi,
    TradesBankApi,
    TransfersBankApi,
    ExternalWalletsBankApi,
    DepositAddressesBankApi,
    DepositBankAccountsBankApi,
    ExternalBankAccountsBankApi,
    WorkflowsBankApi,
)
from cybrid_api_bank.models import (
    Counterparty,
    PostCounterparty,
    PostCounterpartyName,
    PostCounterpartyAliasesInner,
    PostCounterpartyAddress,
    Bank,
    Customer,
    Account,
    DepositAddress,
    PostDepositAddress,
    PostAccount,
    PostCustomer,
    PostIdentityVerification,
    IdentityVerification,
    Quote,
    PostQuote,
    Trade,
    PostTrade,
    Transfer,
    PostTransfer,
    PostTransferParticipant,
    ExternalWallet,
    PostExternalWallet,
    DepositBankAccount,
    PostDepositBankAccount,
    Workflow,
    PostWorkflow,
    ExternalBankAccount,
    PostExternalBankAccount,
    PostExternalBankAccountCounterpartyBankAccount,
)

from app.auth import get_token
from app.config import Config
from app.helpers.exceptions import BadResultError

COUNTRY_CODE_USA = "US"
COUNTRY_CODE_CANADA = "CA"

CUSTOMER_TYPE_INDIVIDUAL = "individual"
CUSTOMER_TYPE_BUSINESS = "business"

COUNTERPARTY_TYPE_INDIVIDUAL = "individual"
COUNTERPARTY_TYPE_BUSINESS = "business"

IDENTITY_VERIFICATION_TYPE_KYC = "kyc"
IDENTITY_VERIFICATION_TYPE_BANK_ACCOUNT = "bank_account"
IDENTITY_VERIFICATION_TYPE_COUNTERPARTY = "counterparty"

IDENTITY_VERIFICATION_METHOD_ID_AND_SELFIE = "id_and_selfie"
IDENTITY_VERIFICATION_METHOD_ACCOUNT_OWNERSHIP = "account_ownership"
IDENTITY_VERIFICATION_WATCHLISTS = "watchlists"

IDENTITY_VERIFICATION_EXPECTED_BEHAVIOUR_PASSED_IMMEDIATELY = "passed_immediately"

STATE_CREATED = "created"
STATE_PENDING = "pending"
STATE_COMPLETED = "completed"
STATE_SETTLING = "settling"
STATE_WAITING = "waiting"
STATE_UNVERIFIED = "unverified"
STATE_VERIFIED = "verified"

OUTCOME_PASSED = "passed"
OUTCOME_FAILED = "failed"

ASSET_CODE_USD = "USD"
ASSET_CODE_USDC = "USDC"

TRADING_PAIR_USDC_USD = "USDC-USD"

ACCOUNT_TYPE_FIAT = "fiat"
ACCOUNT_TYPE_TRADING = "trading"

DEPOSIT_BANK_ACCOUNT_TYPE_MAIN = "main"

WORKFLOW_TYPE_PLAID = "plaid"

WORKFLOW_KIND_TOKEN_CREATE = "link_token_create"

EXTERNAL_BANK_ACCOUNT_KIND_PLAID = "plaid"
EXTERNAL_BANK_ACCOUNT_KIND_RAW_ROUTING_DETAILS = "raw_routing_details"

ROUTING_NUMBER_TYPE_ABA = "ABA"

LANGUAGE_EN = "en"

LINK_CUSTOMIZATION_DEFAULT = "default"

QUOTE_PRODUCT_TYPE_FUNDING = "funding"
QUOTE_PRODUCT_TYPE_TRADING = "trading"
QUOTE_PRODUCT_TYPE_CRYPTO_TRANSFER = "crypto_transfer"
QUOTE_PRODUCT_TYPE_BOOK = "book_transfer"

QUOTE_SIDE_DEPOSIT = "deposit"
QUOTE_SIDE_WITHDRAWAL = "withdrawal"
QUOTE_SIDE_BUY = "buy"

TRANSFER_TYPE_FUNDING = "funding"
TRANSFER_TYPE_CRYPTO = "crypto"
TRANSFER_TYPE_BOOK = "book"

PAYMENT_RAIL_RTP = "rtp"

PARTICIPANT_TYPE_CUSTOMER = "customer"
PARTICIPANT_TYPE_COUNTERPARTY = "counterparty"

logger = logging.getLogger()


def create_logging_handler():
    logging.getLogger().handlers.clear()

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


def create_customer(
    api_client: cybrid_api_bank.ApiClient, customer_type: str
) -> Customer:
    logger.info("Creating customer...")

    api_instance = CustomersBankApi(api_client)
    post_customer = PostCustomer(type=customer_type)

    try:
        # https://docs.cybrid.xyz/reference/createcustomer
        customer = api_instance.create_customer(post_customer)
        logger.info("Created customer: %s", customer.guid)
        return customer
    except cybrid_api_bank.OpenApiException as e:
        logger.error(f"An API error occurred when creating customer: {e}")
        raise e


def get_customer(api_client: cybrid_api_bank.ApiClient, guid: str) -> Customer:
    logger.info("Getting customer: %s", guid)

    api_instance = CustomersBankApi(api_client)

    try:
        # https://docs.cybrid.xyz/reference/getcustomer
        customer = api_instance.get_customer(guid)
        logger.info("Got customer: %s", customer.guid)
        return customer
    except cybrid_api_bank.OpenApiException as e:
        logger.error(f"An API error occurred when getting customer: {e}")
        raise e


def wait_for_customer(
    api_client: cybrid_api_bank.ApiClient,
    customer: Customer,
    expected_states: list[str],
) -> None:
    sleep_count = 0
    customer_state = customer.state
    final_states = expected_states
    while customer_state not in final_states and sleep_count < Config.TIMEOUT:
        time.sleep(1)
        sleep_count += 1
        customer = get_customer(api_client, customer.guid)
        customer_state = customer.state
    if customer_state not in final_states:
        raise BadResultError(f"Customer has invalid state: {customer_state}")

    logger.info(f"Customer successfully created with state {customer_state}")


def create_account(
    api_client: cybrid_api_bank.ApiClient,
    owner: Bank | Customer,
    account_type: str,
    asset: str,
) -> Account:
    logger.info(
        f"Creating {account_type} account for asset {asset} and owner: {owner.guid}"
    )

    kwargs = {}
    if isinstance(owner, Customer):
        kwargs["customer_guid"] = owner.guid

    api_instance = AccountsBankApi(api_client)
    post_account = PostAccount(
        type=account_type,
        asset=asset,
        name=f"{asset} account for {owner.guid}",
        **kwargs,
    )

    try:
        # https://docs.cybrid.xyz/reference/createaccount
        account = api_instance.create_account(post_account)
        logger.info(f"Created {account_type} account: {account.guid}")
        return account
    except cybrid_api_bank.OpenApiException as e:
        logger.error(f"An API error occurred when creating account: {e}")
        raise e


def get_account(api_client: cybrid_api_bank.ApiClient, guid: str) -> Account:
    logger.info("Getting account: %s", guid)

    api_instance = AccountsBankApi(api_client)

    try:
        # https://docs.cybrid.xyz/reference/getaccount
        account = api_instance.get_account(guid)
        logger.info("Got account: %s", account.guid)
        return account
    except cybrid_api_bank.OpenApiException as e:
        logger.error(f"An API error occurred when getting account: {e}")
        raise e


def wait_for_account(
    api_client: cybrid_api_bank.ApiClient, account: Account, expected_states: list[str]
) -> None:
    sleep_count = 0
    account_state = account.state
    final_states = expected_states
    while account_state not in final_states and sleep_count < Config.TIMEOUT:
        time.sleep(1)
        sleep_count += 1
        account = get_account(api_client, account.guid)
        account_state = account.state
    if account_state not in final_states:
        raise BadResultError(f"Account has invalid state: {account_state}")

    logger.info(f"Account successfully created with state {account_state}")


def create_deposit_address(
    api_client: cybrid_api_bank.ApiClient, account: Account
) -> DepositAddress:
    logger.info(f"Creating deposit address for account: {account.guid}")

    api_instance = DepositAddressesBankApi(api_client)
    post_account = PostDepositAddress(account_guid=account.guid)

    try:
        # https://docs.cybrid.xyz/reference/createdepositaddress
        address = api_instance.create_deposit_address(post_account)
        logger.info(f"Created address: {address.guid}")
        return address
    except cybrid_api_bank.OpenApiException as e:
        logger.error(f"An API error occurred when creating account: {e}")
        raise e


def get_deposit_address(
    api_client: cybrid_api_bank.ApiClient, guid: str
) -> DepositAddress:
    logger.info("Getting deposit address: %s", guid)

    api_instance = DepositAddressesBankApi(api_client)

    try:
        # https://docs.cybrid.xyz/reference/getdepositaddress
        address = api_instance.get_deposit_address(guid)
        logger.info("Got deposit address: %s", address.guid)
        return address
    except cybrid_api_bank.OpenApiException as e:
        logger.error(f"An API error occurred when getting deposit address: {e}")
        raise e


def wait_for_deposit_address(
    api_client: cybrid_api_bank.ApiClient,
    address: DepositAddress,
    expected_states: list[str],
) -> None:
    sleep_count = 0
    address_state = address.state
    final_states = expected_states
    while address_state not in final_states and sleep_count < Config.TIMEOUT:
        time.sleep(1)
        sleep_count += 1
        address = get_deposit_address(api_client, address.guid)
        address_state = address.state
    if address_state not in final_states:
        raise BadResultError(f"Deposit address has invalid state: {address_state}")

    logger.info(f"Deposit address successfully created with state {address_state}")


def create_deposit_bank_account(
    api_client: cybrid_api_bank.ApiClient,
    account: Account,
    account_type: str,
) -> DepositBankAccount:
    logger.info(f"Creating deposit bank account for account: {account.guid}")

    api_instance = DepositBankAccountsBankApi(api_client)
    post_account = PostDepositBankAccount(type=account_type, account_guid=account.guid)

    try:
        # https://docs.cybrid.xyz/reference/createdepositbankaccount
        account = api_instance.create_deposit_bank_account(post_account)
        logger.info(f"Created bank account: {account.guid}")
        return account
    except cybrid_api_bank.OpenApiException as e:
        logger.error(f"An API error occurred when creating account: {e}")
        raise e


def get_deposit_bank_account(
    api_client: cybrid_api_bank.ApiClient, guid: str
) -> DepositBankAccount:
    logger.info("Getting bank account: %s", guid)

    api_instance = DepositBankAccountsBankApi(api_client)

    try:
        # https://docs.cybrid.xyz/reference/getdepositbankaccount
        account = api_instance.get_deposit_bank_account(guid)
        logger.info("Got account: %s", account.guid)
        return account
    except cybrid_api_bank.OpenApiException as e:
        logger.error(f"An API error occurred when getting account: {e}")
        raise e


def wait_for_deposit_bank_account(
    api_client: cybrid_api_bank.ApiClient,
    account: DepositBankAccount,
    expected_states: list[str],
) -> None:
    sleep_count = 0
    account_state = account.state
    final_states = expected_states
    while account_state not in final_states and sleep_count < Config.TIMEOUT:
        time.sleep(1)
        sleep_count += 1
        account = get_deposit_bank_account(api_client, account.guid)
        account_state = account.state
    if account_state not in final_states:
        raise BadResultError(f"Deposit account has invalid state: {account_state}")

    logger.info(f"Deposit account successfully created with state {account_state}")


def create_identity_verification(
    api_client: cybrid_api_bank.ApiClient,
    verification_type: str,
    verification_method: str,
    customer: Customer | None = None,
    counterparty: Counterparty | None = None,
    expected_behaviours: list[str] | None = None,
    external_bank_account: ExternalBankAccount | None = None,
) -> IdentityVerification:
    logger.info("Creating identity verification...")

    kwargs = {}
    if customer is not None:
        kwargs["customer_guid"] = customer.guid
    if counterparty is not None:
        kwargs["counterparty_guid"] = counterparty.guid
    if external_bank_account is not None:
        kwargs["external_bank_account_guid"] = external_bank_account.guid

    api_instance = IdentityVerificationsBankApi(api_client)
    post_identity_verification = PostIdentityVerification(
        type=verification_type,
        method=verification_method,
        expected_behaviours=expected_behaviours,
        **kwargs,
    )

    try:
        # https://docs.cybrid.xyz/reference/createidentityverification
        api_response = api_instance.create_identity_verification(
            post_identity_verification
        )
        logger.info("Created identity verification.")
        return api_response
    except cybrid_api_bank.OpenApiException as e:
        logger.error(f"An API error occurred when creating identity verification: {e}")
        raise e


def get_identity_verification(
    api_client: cybrid_api_bank.ApiClient, guid: str
) -> IdentityVerification:
    logger.info("Getting identity verification...")

    api_instance = IdentityVerificationsBankApi(api_client)

    try:
        # https://docs.cybrid.xyz/reference/getidentityverification
        identity_verification = api_instance.get_identity_verification(guid)
        logger.info("Got identity verification: %s", identity_verification.guid)
        return identity_verification
    except cybrid_api_bank.OpenApiException as e:
        logger.error(f"An API error occurred when getting identity verification: {e}")
        raise e


def wait_for_identity_verification(
    api_client: cybrid_api_bank.ApiClient,
    identity_verification: IdentityVerification,
    expected_states: list[str],
) -> None:
    sleep_count = 0
    identity_verification_state = identity_verification.state
    final_states = expected_states
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
    customer: Customer,
    product_type: str,
    side: str | None = None,
    deliver_amount: int | None = None,
    receive_amount: int | None = None,
    symbol: str | None = None,
    asset: str | None = None,
) -> Quote:
    if deliver_amount is not None:
        amount = deliver_amount
    if receive_amount is not None:
        amount = receive_amount

    if symbol is not None:
        logger.info(f"Creating {product_type} quote for {symbol} of {amount}")
    if asset is not None:
        logger.info(f"Creating {product_type} quote for {asset} of {amount}")

    kwargs = {
        "product_type": product_type,
        "customer_guid": customer.guid,
    }

    if symbol is not None:
        kwargs["symbol"] = symbol
    if asset is not None:
        kwargs["asset"] = asset
    if deliver_amount is not None:
        kwargs["deliver_amount"] = deliver_amount
    if receive_amount is not None:
        kwargs["receive_amount"] = receive_amount
    if side is not None:
        kwargs["side"] = side

    api_instance = QuotesBankApi(api_client)
    post_quote = PostQuote(**kwargs)

    try:
        # https://docs.cybrid.xyz/reference/createquote
        api_response = api_instance.create_quote(post_quote)
        logger.info("Created quote.")
        return api_response
    except cybrid_api_bank.OpenApiException as e:
        logger.error(f"An API error occurred when creating quote: {e}")
        raise e


def create_transfer(
    api_client: cybrid_api_bank.ApiClient,
    quote: Quote,
    transfer_type: str,
    source_participant: Customer,
    destination_participant: Customer | Counterparty,
    source_platform_account: Account | None = None,
    destination_platform_account: Account | None = None,
    external_wallet: ExternalWallet | None = None,
    external_bank_account: ExternalBankAccount | None = None,
    payment_rail: str | None = None,
) -> Transfer:
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
    if external_bank_account is not None:
        transfer_params["external_bank_account_guid"] = external_bank_account.guid
    if source_participant is not None:
        transfer_params["source_participants"] = [
            PostTransferParticipant(
                type=PARTICIPANT_TYPE_CUSTOMER,
                amount=quote.deliver_amount,
                guid=source_participant.guid,
            )
        ]
    if destination_participant is not None:
        if isinstance(destination_participant, Counterparty):
            type = PARTICIPANT_TYPE_COUNTERPARTY
        else:
            type = PARTICIPANT_TYPE_CUSTOMER

        transfer_params["destination_participants"] = [
            PostTransferParticipant(
                type=type,
                amount=quote.receive_amount,
                guid=destination_participant.guid,
            )
        ]
    if payment_rail is not None:
        transfer_params["payment_rail"] = payment_rail

    post_transfer = PostTransfer(**transfer_params)

    try:
        # https://docs.cybrid.xyz/reference/createtransfer
        api_response = api_instance.create_transfer(post_transfer)
        logger.info("Created transfer.")
        return api_response
    except cybrid_api_bank.OpenApiException as e:
        logger.error(f"An API error occurred when creating transfer: {e}")
        raise e


def get_transfer(api_client: cybrid_api_bank.ApiClient, guid: str) -> Transfer:
    logger.info("Getting transfer %s", guid)

    api_instance = TransfersBankApi(api_client)

    try:
        # https://docs.cybrid.xyz/reference/gettransfer
        transfer = api_instance.get_transfer(guid)
        logger.info("Got transfer %s", transfer.guid)
        return transfer
    except cybrid_api_bank.OpenApiException as e:
        logger.error(f"An API error occurred when getting transfer: {e}")
        raise e


def wait_for_transfer(
    api_client: cybrid_api_bank.ApiClient,
    transfer: Transfer,
    expected_states: list[str],
) -> None:
    sleep_count = 0
    transfer_state = transfer.state
    final_states = expected_states
    while transfer_state not in final_states and sleep_count < Config.TIMEOUT:
        time.sleep(1)
        sleep_count += 1
        transfer = get_transfer(api_client, transfer.guid)
        transfer_state = transfer.state
    if transfer_state not in final_states:
        raise BadResultError(f"Transfer has invalid state: {transfer_state}")

    logger.info(f"Transfer successfully completed with state {transfer_state}")


def create_trade(api_client: cybrid_api_bank.ApiClient, quote: Quote) -> Trade:
    logger.info("Creating trade for quote %s", quote.guid)

    api_instance = TradesBankApi(api_client)
    post_trade = PostTrade(quote.guid)

    try:
        # https://docs.cybrid.xyz/reference/createtrade
        trade = api_instance.create_trade(post_trade)
        logger.info("Created trade %s", trade.guid)
        return trade
    except cybrid_api_bank.OpenApiException as e:
        logger.error(f"An API error occurred when creating trade: {e}")
        raise e


def get_trade(api_client: cybrid_api_bank.ApiClient, guid: str) -> Trade:
    logger.info("Getting trade %s", guid)

    api_instance = TradesBankApi(api_client)

    try:
        # https://docs.cybrid.xyz/reference/gettrade
        trade = api_instance.get_trade(guid)
        logger.info("Got trade %s", trade.guid)
        return trade
    except cybrid_api_bank.OpenApiException as e:
        logger.error(f"An API error occurred when getting trade: {e}")
        raise e


def wait_for_trade(
    api_client: cybrid_api_bank.ApiClient, trade: Trade, expected_states: list[str]
) -> None:
    sleep_count = 0
    trade_state = trade.state
    final_states = expected_states
    while trade_state not in final_states and sleep_count < Config.TIMEOUT:
        time.sleep(1)
        sleep_count += 1
        trade = get_trade(api_client, trade.guid)
        trade_state = trade.state
    if trade_state not in final_states:
        raise BadResultError(f"Trade has invalid state: {trade_state}")

    logger.info(f"Trade successfully completed with state {trade_state}")


def create_external_wallet(
    api_client: cybrid_api_bank.ApiClient,
    asset: str,
    customer: Customer | None = None,
    counterparty: Counterparty | None = None,
) -> ExternalWallet:
    api_instance = ExternalWalletsBankApi(api_client)

    kwargs = {}
    name = ""

    if customer is not None:
        logger.info(
            f"Creating external wallet for customer {customer.guid} in {asset}..."
        )
        kwargs["customer_guid"] = customer.guid
        name = f"External wallet for {customer.guid}"
    if counterparty is not None:
        logger.info(
            f"Creating external wallet for counterparty {counterparty.guid} in {asset}..."
        )
        kwargs["counterparty_guid"] = counterparty.guid
        name = f"External wallet for {counterparty.guid}"

    body = PostExternalWallet(
        name=name,
        asset=asset,
        address=secrets.token_hex(16),
        tag=secrets.token_hex(16),
        **kwargs,
    )

    try:
        # https://docs.cybrid.xyz/reference/createexternalwallet
        external_wallet = api_instance.create_external_wallet(post_external_wallet=body)
        logger.info("Created external wallet: %s", external_wallet.guid)
        return external_wallet
    except cybrid_api_bank.OpenApiException as e:
        logger.error(f"An API error occurred when creating an external wallet: {e}")
        raise e


def get_external_wallet(api_client, guid):
    logger.info("Getting external wallet...")

    api_instance = ExternalWalletsBankApi(api_client)

    try:
        # https://docs.cybrid.xyz/reference/getexternalwallet
        external_wallet = api_instance.get_external_wallet(guid)
        logger.info("Got external wallet")
        return external_wallet
    except cybrid_api_bank.OpenApiException as e:
        logger.error(f"An API error occurred when getting external wallet: {e}")
        raise e


def wait_for_external_wallet(
    api_client: cybrid_api_bank.ApiClient,
    external_wallet: ExternalWallet,
    expected_states: list[str],
) -> None:
    sleep_count = 0
    external_wallet_state = external_wallet.state
    final_states = expected_states
    while external_wallet_state not in final_states and sleep_count < Config.TIMEOUT:
        time.sleep(1)
        sleep_count += 1
        external_wallet = get_external_wallet(api_client, external_wallet.guid)
        external_wallet_state = external_wallet.state
    if external_wallet_state not in final_states:
        raise BadResultError(
            f"External wallet has invalid state: {external_wallet_state}"
        )

    logger.info(
        f"External wallet successfully completed with state {external_wallet_state}"
    )


def create_workflow(
    api_client: cybrid_api_bank.ApiClient,
    customer: Customer,
    workflow_type: str,
    workflow_kind: str,
) -> Workflow:
    logger.info(f"Creating workflow for customer {customer.guid}...")

    api_instance = WorkflowsBankApi(api_client)

    body = PostWorkflow(
        type=workflow_type,
        kind=workflow_kind,
        customer_guid=customer.guid,
        language=LANGUAGE_EN,
        link_customization_name=LINK_CUSTOMIZATION_DEFAULT,
    )

    try:
        # https://docs.cybrid.xyz/reference/createworkflow
        workflow = api_instance.create_workflow(post_workflow=body)
        logger.info("Created workflow: %s", workflow.guid)
        return workflow
    except cybrid_api_bank.OpenApiException as e:
        logger.error(f"An API error occurred when creating workflow: {e}")
        raise e


def get_workflow(api_client: cybrid_api_bank.ApiClient, guid: str) -> Workflow:
    logger.info("Getting workflow: %s", guid)

    api_instance = WorkflowsBankApi(api_client)

    try:
        # https://docs.cybrid.xyz/reference/getworkflow
        workflow = api_instance.get_workflow(guid)
        logger.info("Got workflow: %s", workflow.guid)
        return workflow
    except cybrid_api_bank.OpenApiException as e:
        logger.error(f"An API error occurred when getting workflow: {e}")
        raise e


def wait_for_workflow(
    api_client: cybrid_api_bank.ApiClient,
    workflow: Workflow,
    expected_states: list[str],
) -> None:
    sleep_count = 0
    customer_state = workflow.state
    final_states = expected_states
    while customer_state not in final_states and sleep_count < Config.TIMEOUT:
        time.sleep(1)
        sleep_count += 1
        workflow = get_workflow(api_client, workflow.guid)
        customer_state = workflow.state
    if customer_state not in final_states:
        raise BadResultError(f"Workflow has invalid state: {customer_state}")

    logger.info(f"Workflow successfully created with state {customer_state}")


def create_plaid_external_bank_account(
    api_client: cybrid_api_bank.ApiClient,
    customer: Customer,
    plaid_public_token: str,
    plaid_account_id: str,
) -> ExternalBankAccount:
    logger.info(f"Creating Plaid external_bank_account for customer {customer.guid}...")

    api_instance = ExternalBankAccountsBankApi(api_client)

    body = PostExternalBankAccount(
        name=f"External bank account for {customer.guid}",
        account_kind=EXTERNAL_BANK_ACCOUNT_KIND_PLAID,
        customer_guid=customer.guid,
        plaid_public_token=plaid_public_token,
        plaid_account_id=plaid_account_id,
    )

    try:
        # https://docs.cybrid.xyz/reference/createexternalbankaccount
        external_bank_account = api_instance.create_external_bank_account(
            post_external_bank_account=body
        )
        logger.info("Created external_bank_account: %s", external_bank_account.guid)
        return external_bank_account
    except cybrid_api_bank.OpenApiException as e:
        logger.error(f"An API error occurred when creating external_bank_account: {e}")
        raise e


def create_raw_external_bank_account(
    api_client: cybrid_api_bank.ApiClient,
    counterparty: Counterparty,
    routing_number: str,
    account_number: str,
) -> ExternalBankAccount:
    logger.info(
        f"Creating raw external_bank_account for counterparty {counterparty.guid}..."
    )

    api_instance = ExternalBankAccountsBankApi(api_client)

    body = PostExternalBankAccount(
        name=f"External bank account for {counterparty.guid}",
        account_kind=EXTERNAL_BANK_ACCOUNT_KIND_RAW_ROUTING_DETAILS,
        counterparty_guid=counterparty.guid,
        counterparty_bank_account=PostExternalBankAccountCounterpartyBankAccount(
            routing_number_type=ROUTING_NUMBER_TYPE_ABA,
            routing_number=routing_number,
            account_number=account_number,
        ),
    )

    try:
        # https://docs.cybrid.xyz/reference/createexternalbankaccount
        external_bank_account = api_instance.create_external_bank_account(
            post_external_bank_account=body
        )
        logger.info("Created external_bank_account: %s", external_bank_account.guid)
        return external_bank_account
    except cybrid_api_bank.OpenApiException as e:
        logger.error(f"An API error occurred when creating external_bank_account: {e}")
        raise e


def get_external_bank_account(
    api_client: cybrid_api_bank.ApiClient, guid: str
) -> ExternalBankAccount:
    logger.info("Getting external_bank_account: %s", guid)

    api_instance = ExternalBankAccountsBankApi(api_client)

    try:
        # https://docs.cybrid.xyz/reference/getexternalbankaccount
        external_bank_account = api_instance.get_external_bank_account(guid)
        logger.info("Got external_bank_account: %s", external_bank_account.guid)
        return external_bank_account
    except cybrid_api_bank.OpenApiException as e:
        logger.error(f"An API error occurred when getting external_bank_account: {e}")
        raise e


def wait_for_external_bank_account(
    api_client: cybrid_api_bank.ApiClient,
    external_bank_account: ExternalBankAccount,
    expected_states: list[str],
) -> None:
    sleep_count = 0
    customer_state = external_bank_account.state
    final_states = expected_states
    while customer_state not in final_states and sleep_count < Config.TIMEOUT:
        time.sleep(1)
        sleep_count += 1
        external_bank_account = get_external_bank_account(
            api_client, external_bank_account.guid
        )
        customer_state = external_bank_account.state
    if customer_state not in final_states:
        raise BadResultError(f"Workflow has invalid state: {customer_state}")

    logger.info(
        f"External bank account successfully created with state {customer_state}"
    )


def create_counterparty(
    api_client: cybrid_api_bank.ApiClient,
    customer: Customer,
    business: dict[str, Any],
    counterparty_type: str,
) -> Counterparty:
    logger.info("Creating counterparty...")

    api_instance = CounterpartiesBankApi(api_client)
    post_counterparty = PostCounterparty(
        type=counterparty_type,
        customer_guid=customer.guid,
        name=PostCounterpartyName(**business["name"]),
        aliases=[PostCounterpartyAliasesInner(**x) for x in business["aliases"]],
        address=PostCounterpartyAddress(**business["address"]),
    )

    try:
        # https://docs.cybrid.xyz/reference/createcounterparty
        counterparty = api_instance.create_counterparty(post_counterparty)
        logger.info("Created counterparty: %s", counterparty.guid)
        return counterparty
    except cybrid_api_bank.OpenApiException as e:
        logger.error(f"An API error occurred when creating counterparty: {e}")
        raise e


def get_counterparty(api_client: cybrid_api_bank.ApiClient, guid: str) -> Counterparty:
    logger.info("Getting counterparty: %s", guid)

    api_instance = CounterpartiesBankApi(api_client)

    try:
        # https://docs.cybrid.xyz/reference/getcounterparty
        counterparty = api_instance.get_counterparty(guid)
        logger.info("Got counterparty: %s", counterparty.guid)
        return counterparty
    except cybrid_api_bank.OpenApiException as e:
        logger.error(f"An API error occurred when getting counterparty: {e}")
        raise e


def wait_for_counterparty(
    api_client: cybrid_api_bank.ApiClient,
    counterparty: Counterparty,
    expected_states: list[str],
) -> None:
    sleep_count = 0
    counterparty_state = counterparty.state
    final_states = expected_states
    while counterparty_state not in final_states and sleep_count < Config.TIMEOUT:
        time.sleep(1)
        sleep_count += 1
        counterparty = get_counterparty(api_client, counterparty.guid)
        counterparty_state = counterparty.state
    if counterparty_state not in final_states:
        raise BadResultError(f"Counterparty has invalid state: {counterparty_state}")

    logger.info(f"Counterparty successfully created with state {counterparty_state}")
