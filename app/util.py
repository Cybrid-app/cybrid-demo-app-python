import uuid
from cryptography.hazmat.primitives import serialization
from datetime import datetime, timedelta, timezone
from jwcrypto import jwk, jwt


def create_jwt(rsa_signing_key, verification_key, customer, bank_guid):
    signing_key = jwk.JWK.from_pem(
        rsa_signing_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )

    algorithm = "RS512"
    kid = verification_key.guid
    customer_guid = customer.guid
    issued_at = datetime.now(timezone.utc)
    expired_at = issued_at + timedelta(days=365)

    attestation_jwt = jwt.JWT(
        header={"alg": algorithm, "kid": kid},
        claims={
            "iss": "http://api.cybrid.app/banks/" + bank_guid,
            "aud": "http://api.cybrid.app",
            "sub": "http://api.cybrid.app/customers/" + customer_guid,
            "iat": int(issued_at.timestamp()),
            "exp": int(expired_at.timestamp()),
            "jti": str(uuid.uuid4()),
        },
        key=signing_key,
        algs=[algorithm],
    )

    attestation_jwt.make_signed_token(signing_key)
    return attestation_jwt.serialize(compact=True)
