import logging

import cybrid_api_bank
from cybrid_api_bank.model.account import Account
from cybrid_api_bank.models import (
    Customer,
    ExternalWallet,
)

from app.helpers.common import (
    create_quote,
    QUOTE_PRODUCT_TYPE_CRYPTO_TRANSFER,
    QUOTE_SIDE_WITHDRAWAL,
    ASSET_CODE_USDC,
    create_transfer,
    TRANSFER_TYPE_CRYPTO,
    wait_for_transfer,
    STATE_COMPLETED,
    get_account,
)

logger = logging.getLogger()


# https://docs.cybrid.xyz/recipes/off-ramping-usdc-to-a-customers-external-wallet
def recipe_off_ramping_usdc(
    api_client: cybrid_api_bank.ApiClient,
    customer: Customer,
    trading_account: Account,
    external_wallet: ExternalWallet,
) -> None:
    #
    # Off-ramping crypto (USDC) to a customer's external wallet
    #
    # This recipe will off-ramp USDC from a customer's trading account to their external
    # wallet.
    #

    #
    # First, a quote of `product_type` `crypto_transfer` must be created with the side set to
    # `withdrawal`.
    #
    # Here we are asking for 25 USDC to be sent to  the customer's external wallet off the
    # platform.
    #
    # **Note:** Creating a quote is a _synchronous_ operation.
    #
    withdrawal_quote = create_quote(
        api_client,
        customer,
        product_type=QUOTE_PRODUCT_TYPE_CRYPTO_TRANSFER,
        side=QUOTE_SIDE_WITHDRAWAL,
        receive_amount=25_000_000,
        asset=ASSET_CODE_USDC,
    )

    #
    # Create a transfer quote
    #
    # The next step is to initiate a `crypto` transfer to execute the withdrawal from
    # the customer's USDC trading account to their external wallet.
    #
    # In Sandbox, this will complete within a few seconds. In reality, this operation
    # will depend on the blockhain and number of confirmations that the platform waits before
    # the transfer is considered complete.
    #
    # For all transfers, source and destination participant(s) must be specified. This
    # ensures that all transfers comply with the Travel Rule (i.e., all ultimate originating
    # beneficiaries and ultimate receiving beneficiaries are known). For a customer withdrawing
    # funds from their trading account to their own external wallet, the source and destination
    # is simply just the customer themselves.
    #

    # Step 1: Initiate the transfer
    deposit_transfer = create_transfer(
        api_client,
        withdrawal_quote,
        transfer_type=TRANSFER_TYPE_CRYPTO,
        external_wallet=external_wallet,
        source_participant=customer,
        destination_participant=customer,
    )

    # Step 2: Wait for the transfer to settle in the `completed` state.
    wait_for_transfer(api_client, deposit_transfer, expected_states=[STATE_COMPLETED])

    # Once the deposit is `completed`, you can check that the customer has 25 less USDC in their
    # trading account by checking the available balance on the account.
    trading_account = get_account(api_client, trading_account.guid)
    logger.info(
        "Available balance in the trading account: %s", trading_account.platform_balance
    )
