#
# Operations covered in this demo application:
#
# 1. Create a verified individual customer
# 2. Create a verified business counterparty
# 3. Create customer accounts
# 4. Create counterparty accounts
# 5. Add a customer's verified external bank account
# 6. Add a customer's external wallet
# 7. Fund the customer's fiat account
# 8. On-ramp to USDC
# 9. Off-ramp USDC to the customer's external wallet
# 10. Off-ramp USD to the customer's external bank account
# 11. Execute a P2P transfer between two customers
# 12. Send a payment to a counterparty's external wallet

import logging

from app.helpers.common import (
    logger,
    create_logging_handler,
    create_api_client,
    ASSET_CODE_USD,
    ASSET_CODE_USDC,
)
from app.helpers.mock_data import create_us_business
from app.recipes.counterparty_payment import recipe_counterparty_payment
from app.recipes.create_counterparty import recipe_create_counterparty
from app.recipes.create_counterparty_accounts import recipe_create_counterparty_accounts
from app.recipes.create_customer_accounts import recipe_create_accounts
from app.recipes.create_external_bank_account import recipe_create_external_bank_account
from app.recipes.create_external_wallet import recipe_create_external_wallet
from app.recipes.fund_fiat_account import recipe_fund_fiat_account
from app.recipes.off_ramping_usd import recipe_off_ramping_usd
from app.recipes.off_ramping_usdc import recipe_off_ramping_usdc
from app.recipes.p2p_transfer import recipe_p2p_transfer
from app.recipes.trade_for_usdc import recipe_trade_for_usdc
from helpers.exceptions import BadResultError
from recipes.create_customer import recipe_create_individual_customer

logger.setLevel(logging.INFO)


def main():
    # Initialize the logger
    create_logging_handler()

    # Get a handler to the API client
    api_client = create_api_client()

    #
    # Create a verified customer
    #

    customer1 = recipe_create_individual_customer(api_client)
    customer2 = recipe_create_individual_customer(api_client)

    #
    # Create accounts for the customer
    #

    customer1_accounts = recipe_create_accounts(
        api_client,
        customer1,
        fiat_asset=ASSET_CODE_USD,
        crypto_asset=ASSET_CODE_USDC,
    )
    customer2_accounts = recipe_create_accounts(
        api_client,
        customer2,
        fiat_asset=ASSET_CODE_USD,
        crypto_asset=ASSET_CODE_USDC,
    )

    #
    # Add a verified external bank account to the customer
    #

    external_bank_account = recipe_create_external_bank_account(api_client, customer1)

    #
    # Deposit $100 USD to the customer's fiat account from their connected account
    #

    recipe_fund_fiat_account(
        api_client, customer1, customer1_accounts.fiat_account, external_bank_account
    )

    #
    # Convert $75 USD to USDC
    #

    recipe_trade_for_usdc(
        api_client,
        customer1,
        customer1_accounts.fiat_account,
        customer1_accounts.trading_account,
    )

    #
    # Add an external wallet for the customer
    #

    external_wallet = recipe_create_external_wallet(api_client, customer1)

    #
    # Off-ramp USDC to the customer's external wallet
    #

    recipe_off_ramping_usdc(
        api_client,
        customer1,
        customer1_accounts.trading_account,
        external_wallet,
    )

    #
    # Off-ramp USD to the customer's verified external bank account
    #

    recipe_off_ramping_usd(
        api_client,
        customer1,
        customer1_accounts.fiat_account,
        external_bank_account,
    )

    #
    # Create a verified counterparty
    #

    counterparty = recipe_create_counterparty(
        api_client,
        customer1,
        business=create_us_business(),
    )

    #
    # Create accounts for the counterparty
    #

    counterparty_accounts = recipe_create_counterparty_accounts(
        api_client, counterparty
    )

    #
    # Execute a P2P transfer between two customers
    #

    recipe_p2p_transfer(
        api_client,
        customer1,
        customer1_accounts.fiat_account,
        customer2,
        customer2_accounts.fiat_account,
    )

    #
    # Execute a crypto payout to a counterparty
    #

    recipe_counterparty_payment(
        api_client,
        customer1,
        customer1_accounts.trading_account,
        counterparty,
        counterparty_accounts.external_wallet,
    )

    logger.info("Test has completed successfully!")


if __name__ == "__main__":
    main()
