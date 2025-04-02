import logging

import cybrid_api_bank
from cybrid_api_bank.models import Customer

from app.helpers.common import (
    create_customer,
    CUSTOMER_TYPE_INDIVIDUAL,
    create_identity_verification,
    IDENTITY_VERIFICATION_TYPE_KYC,
    IDENTITY_VERIFICATION_METHOD_ID_AND_SELFIE,
    IDENTITY_VERIFICATION_EXPECTED_BEHAVIOUR_PASSED_IMMEDIATELY,
    wait_for_identity_verification,
    STATE_COMPLETED,
    wait_for_customer,
    STATE_UNVERIFIED,
    STATE_VERIFIED,
    get_identity_verification,
    OUTCOME_FAILED,
    get_customer,
)
from app.helpers.exceptions import BadResultError

logger = logging.getLogger()


# https://docs.cybrid.xyz/recipes/creating-a-verified-individual-customer
def recipe_create_individual_customer(
    api_client: cybrid_api_bank.ApiClient,
) -> Customer:
    #
    # Create customer
    #
    # This will create a customer of type "individual." To create a business
    # customer, set `customer_type=CUSTOMER_TYPE_BUSINESS`.
    #
    # The customer will initially be in the `storing` state. Before proceeding,
    # wait for the customer to be in the `unverified` state.
    #

    # Step 1: Create the customer
    customer = create_customer(api_client, customer_type=CUSTOMER_TYPE_INDIVIDUAL)

    # Step 2: Wait for the customer to settle in the `unverified` state.
    wait_for_customer(api_client, customer, expected_states=[STATE_UNVERIFIED])

    #
    # Create identity verification
    #
    # This will initiate an identity verification that must be continued in an interactive fashion by
    # the customer through Persona. This applies both for individuals and businesses.
    #
    # In order to verify a customer set the `type` to `kyc` and the `method` to either `id_and_selfie`
    # for individuals (i.e., KYC) or `business_registration` for businesses (i.e., KYB).
    #
    # Identity verification is a four step process:
    # 1. Create the identity verification (https://docs.cybrid.xyz/reference/createidentityverification).
    #    This will immediately create an identity verification in the `storing` state.
    # 2. Poll on the identity verification until it is in the `waiting` state. When in the `waiting` state
    #    read the `persona_inquiry_id` value (https://docs.cybrid.xyz/reference/getidentityverification).
    # 3. Launch the Persona SDK and pass it the `persona_inquiry_id` obtained in the previous step. For a
    #    sample HTML application that launches the Persona SK see here:
    #    https://docs.cybrid.xyz/docs/how-do-i-drive-kyc-manually.
    # 4. Poll on the identity verification until it is in the `completed`. Check the `outcome` of the
    #    identity verification, it will be either `passed` or `failed. If `failed`, the customer cannot
    #    interact with the platform.
    #
    # Once these steps are completed and `state=completed` and `outcome=passed`, the customer state
    # will be `verified`. You can get the state of the customer by retrieving the customer resource
    # (https://docs.cybrid.xyz/reference/getcustomer).
    #
    # If the identity verification goes into the state `expired` then you can create a new identity
    # verification and use the newly created `persona_inquiry_id` to verify the customer. If the
    # identity verification is in the `waiting` state and the customer wants to resume their session,
    # then you can re-use the `persona_inquiry_id` to verify the customer.
    #
    # If the identity verification goes into the state `pending` then it indicates the UBOs associated
    # with the business must complete their KYC before the verification can proceed.
    #
    # To enhance the responsiveness of your application to state changes, you can also register for
    # and receive webhooks for identity verification state changes See the article here:
    # https://docs.cybrid.xyz/docs/webhooks.
    #

    # Step 1: Create the identity verification
    identity_verification = create_identity_verification(
        api_client,
        customer=customer,
        verification_type=IDENTITY_VERIFICATION_TYPE_KYC,
        verification_method=IDENTITY_VERIFICATION_METHOD_ID_AND_SELFIE,
        # Expected behaviours is set here for demo purposes as this script is non-interactive and
        # the Persona flow requires interaction from the customer.
        expected_behaviours=[
            IDENTITY_VERIFICATION_EXPECTED_BEHAVIOUR_PASSED_IMMEDIATELY
        ],
    )

    # Step 2: Wait for the identity verification to go into the `waiting` state
    # wait_for_identity_verification(
    #     api_client, identity_verification, expected_states=[STATE_WAITING]
    # )

    # Step 3: Retrieve the `persona_inquiry_id` and send the customer through the Persona flow
    identity_verification = get_identity_verification(
        api_client, identity_verification.guid
    )
    logger.info(f"Persona inquiry id: {identity_verification.persona_inquiry_id}")

    # Step 4: Wait for the identity verification to go into the `completed` state and chck
    #         the outcome.
    wait_for_identity_verification(
        api_client, identity_verification, expected_states=[STATE_COMPLETED]
    )

    identity_verification = get_identity_verification(
        api_client, identity_verification.guid
    )
    if identity_verification.outcome == OUTCOME_FAILED:
        raise BadResultError(
            f"Identity verification has an unexpected outcome: {identity_verification}."
        )

    #
    # Check the state of the customer
    #
    wait_for_customer(api_client, customer, expected_states=[STATE_VERIFIED])

    customer = get_customer(api_client, customer.guid)

    return customer
