import cybrid_api_bank
from cybrid_api_bank.models import (
    Customer,
    ExternalWallet,
)

from app.helpers.common import (
    create_external_wallet,
    ASSET_CODE_USDC,
    wait_for_external_wallet,
    STATE_COMPLETED,
)


# https://docs.cybrid.xyz/recipes/adding-a-customers-external-wallet
def recipe_create_external_wallet(
    api_client: cybrid_api_bank.ApiClient, customer: Customer
) -> ExternalWallet:
    #
    # Create external wallet
    #
    # Adding a customer's custodial or non-custodial wallet is a straightforward as adding
    # the wallet and waiting for it to settle in the `completed` state.
    #
    # External wallets are scanned when they are added to the Cybrid platform as well as on
    # every transaction involving the wallet. The wallet may be denied by our platform and
    # can end up in the `failed` state. The external wallet can only be used when in the
    # `completed` state.
    #

    # Step 1: Create the external wallet
    external_wallet = create_external_wallet(
        api_client,
        asset=ASSET_CODE_USDC,
        customer=customer,
    )

    # Step 2: Wait for the workflow to settle in the `completed` state.
    wait_for_external_wallet(
        api_client, external_wallet, expected_states=[STATE_COMPLETED]
    )

    return external_wallet
