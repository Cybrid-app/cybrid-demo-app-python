import logging

import cybrid_api_bank
from cybrid_api_bank.models import (
    Customer,
    ExternalBankAccount,
)

from app.helpers.common import (
    create_workflow,
    WORKFLOW_TYPE_PLAID,
    WORKFLOW_KIND_TOKEN_CREATE,
    wait_for_workflow,
    STATE_COMPLETED,
    get_workflow,
    create_plaid_external_bank_account,
    wait_for_external_bank_account,
    STATE_UNVERIFIED,
    create_identity_verification,
    IDENTITY_VERIFICATION_TYPE_BANK_ACCOUNT,
    IDENTITY_VERIFICATION_METHOD_ACCOUNT_OWNERSHIP,
    IDENTITY_VERIFICATION_EXPECTED_BEHAVIOUR_PASSED_IMMEDIATELY,
    wait_for_identity_verification,
)
from app.helpers.plaid import handle_plaid_on_success

logger = logging.getLogger()


# https://docs.cybrid.xyz/recipes/adding-a-customers-verified-external-bank-account
def recipe_create_external_bank_account(
    api_client: cybrid_api_bank.ApiClient, customer: Customer
) -> ExternalBankAccount:
    #
    # Create external bank account
    #
    # This will initiate a workflow that must be continued in an interactive fashion by
    # the customer through Plaid. Once the customer connects their account via Plaid you must
    # initiate a non-interactive identity verification on the connected account to ensure that
    # the connected account is in the same name as the customer, i.e., the holder information
    # on the bank account matches the customer's KYC information.
    #
    # Connected a bank account is an eight step process:
    # 1. Create the workflow (https://docs.cybrid.xyz/reference/createworkflow) with `type` set to
    #    `plaid` and `kind` set to `link_token_create`. This will immediately create a workflow in
    #    the `storing` state.
    # 2. Poll on the workflow until it is in the `completed` state. When in the `completed` state,
    #    read the `plaid_link_token` value (https://docs.cybrid.xyz/reference/getworkflow).
    # 3. Launch the Plaid SDK and pass it the `plaid_link_token` obtained in the previous step. Guide
    #    your customer through the Plaid experience. For help on launching the Plaid SDK see here:
    #    https://docs.cybrid.xyz/docs/integrating-plaid.
    # 4. Capture the `plaid_public_token` and `metadata` in the `onSuccess()` callback from the Plaid
    #    Link SDK when your customer completes the Plaid Link flow.
    # 5. Create an external bank account (https://docs.cybrid.xyz/reference/createexternalbankaccount)
    #    passing it the `plaid_public_token` and the `account_id` parsed from the `metadata` in the
    #    previous step. This will immediately create an external bank account in the `storing` state.
    # 6. Poll on the external bank account until it is in the `unverified` state
    #    (https://docs.cybrid.xyz/reference/getexternalbankaccount).
    # 7. Create an identity verification (https://docs.cybrid.xyz/reference/createidentityverification)
    #    with `type` set to `bank_account` and `method` set to `account_ownership`. This will immediately
    #    create an identity verification in the `storing` state.
    # 8. Poll on the identity verification until it is in the `completed` state
    #    (https://docs.cybrid.xyz/reference/getidentityverification).
    #
    # If the identity verification is in the `waiting` state it indicates that the verification requires
    # manual review by our Compliance team. In Sandbox, this will occur for all `bank_account` type
    # verifications so you'll want to use the `expected_behaviours` parameter to pass the verification.
    #
    # Once these steps are completed, the external bank account's state will be `verified`. You can get
    # the state of the external bank account by retrieving the external bank account resource
    # (https://docs.cybrid.xyz/reference/getexternalbankaccount).
    #
    # To enhance the responsiveness of your application to state changes, you can also register for
    # and receive webhooks for identity verification state changes See the article here:
    # https://docs.cybrid.xyz/docs/webhooks.
    #

    # Step 1: Create the workflow
    workflow = create_workflow(
        api_client,
        customer,
        workflow_type=WORKFLOW_TYPE_PLAID,
        workflow_kind=WORKFLOW_KIND_TOKEN_CREATE,
    )

    # Step 2: Wait for the workflow to settle in the `completed` state.
    wait_for_workflow(api_client, workflow, expected_states=[STATE_COMPLETED])

    # Step 3: Retrieve the `plaid_link_token` and send the customer through the Plaid Link flow
    workflow = get_workflow(api_client, workflow.guid)
    logger.info(f"Plaid Link token: {workflow.plaid_link_token}")

    # Step 4: Capture the `plaid_public_token` and `account_id` from the `metadata` in the
    #         data passed to the `onSuccess()` callback.
    plaid_public_token, plaid_account_id = handle_plaid_on_success()

    # Step 5: Create the external bank account
    external_bank_account = create_plaid_external_bank_account(
        api_client, customer, plaid_public_token, plaid_account_id
    )

    # Step 6: Wait for the external bank account to settle in the `unverified` state
    wait_for_external_bank_account(
        api_client, external_bank_account, expected_states=[STATE_UNVERIFIED]
    )

    # Step 7: Create the identity verification
    identity_verification = create_identity_verification(
        api_client,
        customer=customer,
        verification_type=IDENTITY_VERIFICATION_TYPE_BANK_ACCOUNT,
        verification_method=IDENTITY_VERIFICATION_METHOD_ACCOUNT_OWNERSHIP,
        # Expected behaviours is set here because otherwise the identity verification will go into
        # the `waiting` state, which requires manual review and Sandbox is not monitored for manual
        # reviews on our side.
        expected_behaviours=[
            IDENTITY_VERIFICATION_EXPECTED_BEHAVIOUR_PASSED_IMMEDIATELY
        ],
        external_bank_account=external_bank_account,
    )

    # Step 8: Wait for the identity verification to go into the `completed` state
    wait_for_identity_verification(
        api_client, identity_verification, expected_states=[STATE_COMPLETED]
    )

    #
    # Check the state of the external bank account
    #
    wait_for_external_bank_account(
        api_client, external_bank_account, expected_states=[STATE_COMPLETED]
    )

    return external_bank_account
