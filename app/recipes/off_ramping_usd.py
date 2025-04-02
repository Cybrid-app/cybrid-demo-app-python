import logging

import cybrid_api_bank
from cybrid_api_bank.models import (
    Account,
    Customer,
    ExternalBankAccount,
)

from app.helpers.common import (
    create_quote,
    QUOTE_SIDE_WITHDRAWAL,
    create_transfer,
    wait_for_transfer,
    STATE_COMPLETED,
    get_account,
    QUOTE_PRODUCT_TYPE_FUNDING,
    ASSET_CODE_USD,
    TRANSFER_TYPE_FUNDING,
    PAYMENT_RAIL_RTP,
)

logger = logging.getLogger()


# https://docs.cybrid.xyz/recipes/off-ramping-usd-to-a-customers-verified-bank-account
def recipe_off_ramping_usd(
    api_client: cybrid_api_bank.ApiClient,
    customer: Customer,
    fiat_account: Account,
    external_bank_account: ExternalBankAccount,
) -> None:
    #
    # Off-ramping fiat (USD) to a customer's external bank account via RTP
    #
    # This recipe will off-ramp USD from a customer's fiat account to their verified external
    # bank account.
    #

    #
    # First, a quote of `product_type` `funding` must be created with the side set to `withdrawal`.
    #
    # Here we are asking for 15 USD to be sent to  the customer's verfied external bank account off
    # the platform.
    #
    # **Note:** Creating a quote is a _synchronous_ operation.
    #
    withdrawal_quote = create_quote(
        api_client,
        customer,
        product_type=QUOTE_PRODUCT_TYPE_FUNDING,
        side=QUOTE_SIDE_WITHDRAWAL,
        receive_amount=15_00,
        asset=ASSET_CODE_USD,
    )

    #
    # Create a transfer quote
    #
    # The next step is to initiate a `funding` transfer to execute the withdrawal from the customer's
    # USD fiat account to their external bank account.
    #
    # In Sandbox, this will complete within a few seconds. In reality, this operation
    # will take some time to execute. In the US, ACHs will settle same business day, however,
    # if executed outside of business hours, on weekends, or on holidays, this transfer will
    # not complete until the next business day. Additionally, in Canada, EFTs will settle in
    # t+1 or t+2 business days. Wires, in both countries, will settle same-day if initiated
    # before 4pm Eastern. RTP and FedNow, in the US, will settle 24/7/365 in about 15 minutes.
    #
    # For all transfers, source and destination participant(s) must be specified. This
    # ensures that all transfers comply with the Travel Rule (i.e., all ultimate originating
    # beneficiaries and ultimate receiving beneficiaries are known). For a customer depositing
    # funds from their bank account to their fiat account, the source and destination is
    # simply just the customer themselves.
    #

    # Step 1: Initiate the transfer, specifying the `payment_rail` as `rtp`
    deposit_transfer = create_transfer(
        api_client,
        withdrawal_quote,
        transfer_type=TRANSFER_TYPE_FUNDING,
        external_bank_account=external_bank_account,
        source_participant=customer,
        destination_participant=customer,
        payment_rail=PAYMENT_RAIL_RTP,
    )

    # Step 2: Wait for the transfer to settle in the `completed` state.
    wait_for_transfer(api_client, deposit_transfer, expected_states=[STATE_COMPLETED])

    # Once the withdrawal is `completed`, you can check that the customer has 15 less USD in their
    # fiat account by checking the available balance on the account.
    fiat_account = get_account(api_client, fiat_account.guid)
    logger.info(
        "Available balance in the fiat account: %s", fiat_account.platform_available
    )
