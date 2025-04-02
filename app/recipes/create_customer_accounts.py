import logging

import cybrid_api_bank
from cybrid_api_bank.models import (
    Account,
    DepositAddress,
    DepositBankAccount,
    Customer,
)

from app.helpers.common import (
    create_account,
    ACCOUNT_TYPE_FIAT,
    STATE_CREATED,
    wait_for_account,
    ACCOUNT_TYPE_TRADING,
    create_deposit_address,
    wait_for_deposit_address,
    create_deposit_bank_account,
    wait_for_deposit_bank_account,
    get_deposit_address,
    get_deposit_bank_account,
    DEPOSIT_BANK_ACCOUNT_TYPE_MAIN,
)

logger = logging.getLogger()


class CustomerAccounts:
    def __init__(
        self,
        fiat_account: Account,
        trading_account: Account,
        deposit_address: DepositAddress,
        deposit_bank_account: DepositBankAccount,
    ):
        self.fiat_account = fiat_account
        self.trading_account = trading_account
        self.deposit_address = deposit_address
        self.deposit_bank_account = deposit_bank_account


# https://docs.cybrid.xyz/recipes/creating-customer-accounts-on-the-platform
def recipe_create_accounts(
    api_client: cybrid_api_bank.ApiClient,
    customer: Customer,
    fiat_asset: str,
    crypto_asset: str,
) -> CustomerAccounts:
    #
    # Create a fiat account
    #
    # This will create a new USD fiat account for the customer.
    #
    # The account will initially be in the `storing` state. Before proceeding,
    # wait for the account to be in the `created` state.
    #

    fiat_account = create_account(
        api_client, owner=customer, account_type=ACCOUNT_TYPE_FIAT, asset=fiat_asset
    )
    wait_for_account(api_client, fiat_account, expected_states=[STATE_CREATED])

    #
    # Create a trading account
    #
    # This will create a new USDC trading account for the customer.
    #
    # The account will initially be in the `storing` state. Before proceeding,
    # wait for the account to be in the `created` state.
    #

    trading_account = create_account(
        api_client,
        owner=customer,
        account_type=ACCOUNT_TYPE_TRADING,
        asset=crypto_asset,
    )
    wait_for_account(api_client, trading_account, expected_states=[STATE_CREATED])

    #
    # Create a deposit address
    #
    # This will create a new USDC wallet address to receive USDC on the Ethereum chain.
    #
    # The account will initially be in the `storing` state. Before proceeding,
    # wait for the address to be in the `created` state.
    #

    deposit_address = create_deposit_address(api_client, trading_account)
    wait_for_deposit_address(
        api_client, deposit_address, expected_states=[STATE_CREATED]
    )

    #
    # Display the USDC wallet address
    #

    deposit_address = get_deposit_address(api_client, deposit_address.guid)
    logger.info(f"Deposit address: {deposit_address.address}")

    #
    # Create a deposit bank account
    #
    # This will open a bank account in the customer's name because `type` is
    # set to `main`. There are costs associated with creating and maintaining `main`
    # deposit bank accounts. Please consult our guid on Deposit Bank Accounts,
    # https://docs.cybrid.xyz/docs/creating-deposit-accounts.
    #
    # As an alternative, a single `main` Deposit Bank Account can be created at
    # the bank-level and sub accounts can be created under the single `main` account
    # for each customer. Deposits are routed to the correct customer through the
    # `unique_memo_id` that is assigned to the customer. The advantage is savings in
    # cost, however, customer deposits that are missing the correct memo will be
    # deposited into the bank's fiat account and it is left to you to correlate the
    # deposit to the correct customer and book transfer the amount to the customer's
    # fiat account.
    #
    # The account will initially be in the `storing` state. Before proceeding,
    # wait for the address to be in the `created` state.
    #

    deposit_bank_account = create_deposit_bank_account(
        api_client,
        fiat_account,
        account_type=DEPOSIT_BANK_ACCOUNT_TYPE_MAIN,
    )
    wait_for_deposit_bank_account(
        api_client, deposit_bank_account, expected_states=[STATE_CREATED]
    )

    #
    # Display the bank account deposit information
    #

    deposit_bank_account = get_deposit_bank_account(
        api_client, deposit_bank_account.guid
    )
    logger.info("Bank account deposit information:")
    logger.info("\tRouting details:")
    logger.info(
        "\t\tRouting number type: %s",
        deposit_bank_account.routing_details[0].routing_number_type,
    )
    logger.info(
        "\t\tRouting number: %s", deposit_bank_account.routing_details[0].routing_number
    )
    logger.info("\tAccount details:")
    logger.info(
        "\t\tAccount number: %s", deposit_bank_account.account_details[0].account_number
    )
    logger.info("\tBeneficiary name: %s", deposit_bank_account.counterparty_name)
    logger.info("\tBeneficiary address:")
    logger.info("\t\tStreet 1: %s", deposit_bank_account.counterparty_address.street)
    if deposit_bank_account.counterparty_address.street2 is not None:
        logger.info(
            "\t\tStreet 2: %s", deposit_bank_account.counterparty_address.street2
        )
    logger.info("\t\tCity: %s", deposit_bank_account.counterparty_address.city)
    logger.info(
        "\t\tSubdivision: %s", deposit_bank_account.counterparty_address.subdivision
    )
    logger.info(
        "\t\tPostal code: %s", deposit_bank_account.counterparty_address.postal_code
    )
    logger.info(
        "\t\tCountry code: %s", deposit_bank_account.counterparty_address.country_code
    )
    logger.info("\tMemo: %s", deposit_bank_account.unique_memo_id)

    return CustomerAccounts(
        fiat_account=fiat_account,
        trading_account=trading_account,
        deposit_address=deposit_address,
        deposit_bank_account=deposit_bank_account,
    )
