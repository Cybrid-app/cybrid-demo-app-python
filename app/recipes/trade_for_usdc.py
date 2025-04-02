import logging

import cybrid_api_bank
from cybrid_api_bank.models import (
    Customer,
    Account,
)

from app.helpers.common import (
    create_quote,
    QUOTE_PRODUCT_TYPE_TRADING,
    QUOTE_SIDE_BUY,
    TRADING_PAIR_USDC_USD,
    create_trade,
    STATE_SETTLING,
    wait_for_trade,
    get_account,
)

logger = logging.getLogger()


# https://docs.cybrid.xyz/recipes/on-ramping-to-usdc
def recipe_trade_for_usdc(
    api_client: cybrid_api_bank.ApiClient,
    customer: Customer,
    fiat_account: Account,
    trading_account: Account,
) -> None:
    #
    # Fund a customer's USDC trading account
    #
    # This recipe will fund a customer's USDC trading account by trading their USD
    # for USDC.
    #

    #
    # First, a quote of `product_type` `trading` must be created with the side set to
    # `buy`.
    #
    # Here we are asking for $75 USD to be converted to USDC and the USDC deposited
    # into the customer's trading account.
    #
    # The returned trade will display the fee charged for the trade. This is a unified
    # fee that combines both the fee that you are charging your customer for the trade
    # as well as the fee that we are charging for the trade. The fee should be shown to
    # the customer.
    #
    # To enhance the responsiveness of your application to state changes, you can also register for
    # and receive webhooks for trade state changes See the article here:
    # https://docs.cybrid.xyz/docs/webhooks.
    #
    # **Note:** Creating a quote is a _synchronous_ operation.
    #
    buy_quote = create_quote(
        api_client,
        customer,
        product_type=QUOTE_PRODUCT_TYPE_TRADING,
        side=QUOTE_SIDE_BUY,
        deliver_amount=75_00,
        symbol=TRADING_PAIR_USDC_USD,
    )
    logger.info(
        "Converting %d USD for %d USDC with a fee of %d USD (all amounts in base units)",
        buy_quote.deliver_amount,
        buy_quote.receive_amount,
        buy_quote.fee,
    )

    #
    # Executing a trade
    #
    # The next step is to execute a trade in order to convert the customer's USD for USDC.
    #
    # In Sandbox, the trade will go to the `settling` state in a few seconds. In Sandbox,
    # `settling` should be considered a terminal state and the trade should be treated as
    # completed in Sandbox. In Production, trades will transition from `settling` to
    # `completed` when the trade has been settled. In Production, `completed` should be
    # treated as the terminal state.
    #

    # Step 1: Execute the trade
    trade = create_trade(api_client, buy_quote)

    # Step 2: Wait for the trade to settle in the `settling` state.
    wait_for_trade(api_client, trade, expected_states=[STATE_SETTLING])

    # Once the trade is in the `settling` state, you can check that:
    #
    # 1. The customer no longer has any USD in their fiat account
    # 2. The customer has USDC in their trading account
    #
    fiat_account = get_account(api_client, fiat_account.guid)
    trading_account = get_account(api_client, trading_account.guid)

    logger.info(
        "Available balance in the fiat account: %s", fiat_account.platform_available
    )
    logger.info("Balance in the trading account: %s", trading_account.platform_balance)
