from typing import Any

import cybrid_api_bank
from cybrid_api_bank.models import (
    Customer,
    Counterparty,
)

from app.helpers.common import (
    create_counterparty,
    COUNTERPARTY_TYPE_BUSINESS,
    wait_for_counterparty,
    STATE_UNVERIFIED,
    create_identity_verification,
    IDENTITY_VERIFICATION_TYPE_COUNTERPARTY,
    IDENTITY_VERIFICATION_WATCHLISTS,
    wait_for_identity_verification,
    STATE_COMPLETED,
    get_identity_verification,
    OUTCOME_FAILED,
    STATE_VERIFIED,
    get_counterparty,
)
from app.helpers.exceptions import BadResultError


# https://docs.cybrid.xyz/recipes/creating-a-verified-business-counterparty
def recipe_create_counterparty(
    api_client: cybrid_api_bank.ApiClient,
    customer: Customer,
    business: dict[str, Any],
) -> Counterparty:
    #
    # Create counterparty
    #
    # This will create a counterparty of type "business." To create an individual
    # counterparty, set `counterparty_type=COUNTERPARTY_TYPE_INDIVIDUAL`.
    #
    # The counterparty will initially be in the `storing` state. Before proceeding,
    # wait for the counterparty to be in the `unverified` state.
    #

    # Step 1: Create the counterparty
    counterparty = create_counterparty(
        api_client, customer, business, counterparty_type=COUNTERPARTY_TYPE_BUSINESS
    )

    # Step 2: Wait for the counterparty to settle in the `unverified` state.
    wait_for_counterparty(api_client, counterparty, expected_states=[STATE_UNVERIFIED])

    #
    # Create identity verification
    #
    # This will initiate an identity verification that will execute in a non-interactive fashion. This
    # applies both for individuals and businesses.
    #
    # In order to verify a counterparty set the `type` to `counterparty` and the `method` to `watchlists`
    # for individuals and businesses.
    #
    # Identity verification is a two step process:
    # 1. Create the identity verification (https://docs.cybrid.xyz/reference/createidentityverification).
    #    This will immediately create an identity verification in the `storing` state.
    # 2. Poll on the identity verification until it is in the `completed`. Check the `outcome` of the
    #    identity verification, it will be either `passed` or `failed. If `failed`, the counterparty cannot
    #    interact with the platform.
    #
    # Once these steps are completed and `state=completed` and `outcome=passed`, the counterparty state
    # will be `verified`. You can get the state of the counterparty by retrieving the counterparty resource
    # (https://docs.cybrid.xyz/reference/getcounterparty).
    #
    # To enhance the responsiveness of your application to state changes, you can also register for
    # and receive webhooks for identity verification state changes See the article here:
    # https://docs.cybrid.xyz/docs/webhooks.
    #

    # Step 1: Create the identity verification
    identity_verification = create_identity_verification(
        api_client,
        counterparty=counterparty,
        verification_type=IDENTITY_VERIFICATION_TYPE_COUNTERPARTY,
        verification_method=IDENTITY_VERIFICATION_WATCHLISTS,
    )

    # Step 2: Wait for the identity verification to go into the `completed` state and chck
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
    # Check the state of the counterparty
    #
    wait_for_counterparty(api_client, counterparty, expected_states=[STATE_VERIFIED])

    counterparty = get_counterparty(api_client, counterparty.guid)

    return counterparty
