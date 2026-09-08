from datetime import timedelta

from jose import jwt

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token, decode_token


def test_access_token_contains_required_claims() -> None:
    token = create_access_token({"sub": "engineer", "email": "engineer@utz.local"})

    payload = decode_token(token)

    assert payload is not None
    assert payload["sub"] == "engineer"
    assert payload["type"] == "access"
    assert payload["iss"] == settings.JWT_ISSUER
    assert payload["aud"] == settings.JWT_AUDIENCE
    assert payload["jti"]
    assert payload["iat"]


def test_refresh_token_has_distinct_type_and_jti() -> None:
    access = decode_token(create_access_token({"sub": "engineer"}))
    refresh = decode_token(create_refresh_token({"sub": "engineer"}))

    assert access is not None
    assert refresh is not None
    assert refresh["type"] == "refresh"
    assert refresh["jti"] != access["jti"]


def test_expired_token_is_rejected() -> None:
    token = create_access_token({"sub": "engineer"}, expires_delta=timedelta(seconds=-1))

    assert decode_token(token) is None


def test_token_with_wrong_audience_is_rejected() -> None:
    token = jwt.encode(
        {
            "sub": "engineer",
            "type": "access",
            "iss": settings.JWT_ISSUER,
            "aud": "another-service",
        },
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )

    assert decode_token(token) is None
