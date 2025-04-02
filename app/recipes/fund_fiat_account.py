import logging

import cybrid_api_bank
from cybrid_api_bank.model.account import Account
from cybrid_api_bank.models import (
    Customer,
    ExternalBankAccount,
)

from app.helpers.common import (
    create_quote,
    QUOTE_PRODUCT_TYPE_FUNDING,
    QUOTE_SIDE_DEPOSIT,
    ASSET_CODE_USD,
    create_transfer,
    TRANSFER_TYPE_FUNDING,
    STATE_COMPLETED,
    wait_for_transfer,
    get_account,
)

logger = logging.getLogger()


# https://docs.cybrid.xyz/recipes/funding-a-customers-fiat-account
def recipe_fund_fiat_account(
    api_client: cybrid_api_bank.ApiClient,
    customer: Customer,
    fiat_account: Account,
    external_bank_account: ExternalBankAccount,
) -> None:
    #
    # Fund a customer's fiat account
    #
    # This recipe will fund a customer's fiat account from their connected and
    # verified external bank account.
    #

    #
    # First, a quote of `product_type` `funding` must be created with the side set to
    # `deposit`.
    #
    # Here we are asking for $100 USD to be received into the customer's fiat account
    # on the platform.
    #
    # **Note:** Creating a quote is a _synchronous_ operation.
    #
    deposit_quote = create_quote(
        api_client,
        customer,
        product_type=QUOTE_PRODUCT_TYPE_FUNDING,
        side=QUOTE_SIDE_DEPOSIT,
        receive_amount=100_00,
        asset=ASSET_CODE_USD,
    )

    #
    # Create a transfer quote
    #
    # The next step is to initiate a `funding` transfer to execute the deposit from
    # the customer's Plaid-connected external bank account to their fiat account.
    #
    # In Sandbox, this will complete within a few seconds. In reality, this operation
    # will take some time to execute. In the US, ACHs will settle same business day, however,
    # if executed outside of business hours, on weekends, or on holidays, this transfer will
    # not complete until the next business day. Additionally, in Canada, EFTs will settle in
    # t+1 or t+2 business days.
    #
    # For all transfers, source and destination participant(s) must be specified. This
    # ensures that all transfers comply with the Travel Rule (i.e., all ultimate originating
    # beneficiaries and ultimate receiving beneficiaries are known). For a customer depositing
    # funds from their bank account to their fiat account, the source and destination is
    # simply just the customer themselves.
    #
    # To enhance the responsiveness of your application to state changes, you can also register for
    # and receive webhooks for transfer state changes See the article here:
    # https://docs.cybrid.xyz/docs/webhooks.
    #

    # Step 1: Initiate the transfer
    deposit_transfer = create_transfer(
        api_client,
        deposit_quote,
        transfer_type=TRANSFER_TYPE_FUNDING,
        external_bank_account=external_bank_account,
        source_participant=customer,
        destination_participant=customer,
    )

    # Step 2: Wait for the transfer to settle in the `completed` state.
    wait_for_transfer(api_client, deposit_transfer, expected_states=[STATE_COMPLETED])

    # Once the deposit is `completed`, you can check that the customer has their $100 USD in their
    # fiat account by checking the available balance on the account.
    fiat_account = get_account(api_client, fiat_account.guid)
    logger.info(
        "Available balance in the fiat account: %s", fiat_account.platform_available
    )
