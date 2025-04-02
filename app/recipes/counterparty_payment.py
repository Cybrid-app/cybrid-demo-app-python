import logging

import cybrid_api_bank
from cybrid_api_bank.models import (
    Account,
    Customer,
    Counterparty,
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


# https://docs.cybrid.xyz/recipes/send-a-payment-to-a-counterpartys-external-wallet
def recipe_counterparty_payment(
    api_client: cybrid_api_bank.ApiClient,
    customer: Customer,
    customer_trading_account: Account,
    counterparty: Counterparty,
    counterparty_external_wallet: ExternalWallet,
) -> None:
    #
    # Making a USDC payment to a counterparty's external wallet
    #
    # This recipe will make a USDC payment from a customer's trading account to the counterparty's
    # USDC wallet.
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
    # Create a crypto transfer
    #
    # The next step is to initiate a `crypto` transfer to execute the withdrawal from
    # the customer's USDC trading account to the counterparty's wallet.
    #
    # In Sandbox, this will complete within a few seconds. In reality, this operation
    # will depend on the blockchain and number of confirmations that the platform waits before
    # the transfer is considered complete.
    #
    # For all transfers, source and destination participant(s) must be specified. This
    # ensures that all transfers comply with the Travel Rule (i.e., all ultimate originating
    # beneficiaries and ultimate receiving beneficiaries are known). For a customer making a
    # payment from their trading account to a counterparty, the source is the customer and the
    # destination is the counterparty.
    #

    # Step 1: Initiate the transfer
    deposit_transfer = create_transfer(
        api_client,
        withdrawal_quote,
        transfer_type=TRANSFER_TYPE_CRYPTO,
        external_wallet=counterparty_external_wallet,
        source_participant=customer,
        destination_participant=counterparty,
    )

    # Step 2: Wait for the transfer to settle in the `completed` state.
    wait_for_transfer(api_client, deposit_transfer, expected_states=[STATE_COMPLETED])

    # Once the deposit is `completed`, you can check that the customer has 25 less USDC in their
    # trading account by checking the available balance on the account.
    trading_account = get_account(api_client, customer_trading_account.guid)
    logger.info(
        "Available balance in the trading account: %s", trading_account.platform_balance
    )
