import logging

import cybrid_api_bank
from cybrid_api_bank.model.account import Account
from cybrid_api_bank.model.customer import Customer

from app.helpers.common import (
    create_quote,
    QUOTE_PRODUCT_TYPE_BOOK,
    ASSET_CODE_USD,
    create_transfer,
    TRANSFER_TYPE_BOOK,
    wait_for_transfer,
    STATE_COMPLETED,
    get_account,
)

logger = logging.getLogger()


# https://docs.cybrid.xyz/recipes/executing-a-p2p-transfer-between-customers
def recipe_p2p_transfer(
    api_client: cybrid_api_bank.ApiClient,
    customer1: Customer,
    customer1_fiat_account: Account,
    customer2: Customer,
    customer2_fiat_account: Account,
) -> None:
    #
    # Book transferring fiat (USD) between two customer fiat accounts
    #
    # This recipe will book transfer USD between two customer fiat accounts.
    #

    #
    # First, a quote of `product_type` `book_transfer` must be created.
    #
    # Here we are asking for 5 USD to be sent from one customer's fiat account to another customer's
    # fiat account.
    #
    # **Note:** Creating a quote is a _synchronous_ operation.
    #
    book_transfer_quote = create_quote(
        api_client,
        customer1,
        product_type=QUOTE_PRODUCT_TYPE_BOOK,
        receive_amount=5_00,
        asset=ASSET_CODE_USD,
    )

    #
    # Execute a book transfer
    #
    # The next step is to initiate a `book` transfer to execute the transfer of fiat from one
    # customer's USD fiat account to another customer's fiat account.
    #
    # Both in Sandbox and Production this will complete in a few seconds.
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
    book_transfer = create_transfer(
        api_client,
        book_transfer_quote,
        transfer_type=TRANSFER_TYPE_BOOK,
        source_platform_account=customer1_fiat_account,
        destination_platform_account=customer2_fiat_account,
        source_participant=customer1,
        destination_participant=customer2,
    )

    # Step 2: Wait for the transfer to settle in the `completed` state.
    wait_for_transfer(api_client, book_transfer, expected_states=[STATE_COMPLETED])

    # Once the transfer is `completed`, you can check that customer1 has 5 less USD in their
    # fiat account by checking the available balance on the account. You can also check that
    # customer2 has 5 more USD in their account.
    customer1_fiat_account = get_account(api_client, customer1_fiat_account.guid)
    logger.info(
        "Available balance in customer1's fiat account: %s",
        customer1_fiat_account.platform_available,
    )

    customer2_fiat_account = get_account(api_client, customer2_fiat_account.guid)
    logger.info(
        "Available balance in customer2's fiat account: %s",
        customer2_fiat_account.platform_available,
    )
