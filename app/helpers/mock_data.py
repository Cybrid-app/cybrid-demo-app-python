import secrets
from typing import Any

from faker import Faker
from faker_e164.providers import E164Provider

from app.helpers.common import COUNTRY_CODE_USA

FAKER = Faker()
FAKER.add_provider(E164Provider)


def create_us_business() -> dict[str, Any]:
    name = FAKER.company()
    dba = secrets.choice((FAKER.company(), None))

    return dict(
        name=dict(full=name),
        aliases=[dict(full=dba)] if dba is not None else [],
        address=dict(
            street=FAKER.street_address(),
            street2=secrets.choice((FAKER.building_number(), None)),
            city=FAKER.city(),
            subdivision=secrets.choice(("IL", "NY")),
            postal_code=FAKER.postcode(),
            country_code=COUNTRY_CODE_USA,
        ),
        email_address=FAKER.email(),
        phone_number=FAKER.safe_e164(region_code=COUNTRY_CODE_USA),
    )
