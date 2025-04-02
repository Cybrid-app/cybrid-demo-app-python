import secrets
import string

import cybrid_api_bank
from cybrid_api_bank.model.external_bank_account import ExternalBankAccount
from cybrid_api_bank.model.external_wallet import ExternalWallet
from cybrid_api_bank.models import (
    Counterparty,
)

from app.helpers.common import (
    create_external_wallet,
    ASSET_CODE_USDC,
    wait_for_external_wallet,
    STATE_COMPLETED,
    get_external_wallet,
    create_raw_external_bank_account,
    wait_for_external_bank_account,
    get_external_bank_account,
)

ROUTING_NUMBER_TEST_FI = "021000021"


class CounterpartyAccounts:
    def __init__(
        self,
        external_wallet: ExternalWallet,
        external_bank_account: ExternalBankAccount,
    ):
        self.external_wallet = external_wallet
        self.external_bank_account = external_bank_account


# https://docs.cybrid.xyz/recipes/adding-counterparty-accounts-to-the-platform
def recipe_create_counterparty_accounts(
    api_client: cybrid_api_bank.ApiClient,
    counterparty: Counterparty,
) -> CounterpartyAccounts:
    #
    # Create external wallet
    #
    # Adding a counterparty's custodial or non-custodial wallet is a straightforward as adding
    # the wallet and waiting for it to settle in the `completed` state. This is the same
    # process that is used to add a customer's external wallet.
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
        counterparty=counterparty,
    )

    # Step 2: Wait for the workflow to settle in the `completed` state.
    wait_for_external_wallet(
        api_client, external_wallet, expected_states=[STATE_COMPLETED]
    )

    #
    # Create external bank account
    #
    # Counterparty external bank accounts must be added using raw routing details. The counterparty's
    # KYC/ KYB details will automatically be used as the beneficiary information on the account and,
    # therefore, do not need to be supplied via the API.
    #
    # Moreover, since this bank account is being added explicitly as a counterparty external bank
    # account it does not need to go through the identity verification process.
    #

    # Step 1: Create the raw routing details external bank account
    external_bank_account = create_raw_external_bank_account(
        api_client,
        counterparty=counterparty,
        routing_number=ROUTING_NUMBER_TEST_FI,
        account_number="".join(secrets.choice(string.digits) for _ in range(3)),
    )

    # Step 2: Wait for the external bank account to settle in the `completed` state.
    wait_for_external_bank_account(
        api_client, external_bank_account, expected_states=[STATE_COMPLETED]
    )

    return CounterpartyAccounts(
        external_wallet=get_external_wallet(api_client, external_wallet.guid),
        external_bank_account=get_external_bank_account(
            api_client, external_bank_account.guid
        ),
    )
