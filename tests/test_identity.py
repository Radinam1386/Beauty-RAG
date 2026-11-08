from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import Response

from app.auth.identity import resolve_guest
from app.auth.jwt import AuthError, decode_token
from app.core.config import Settings

SECRET = "unit-secret"


def settings(**overrides) -> Settings:
    base = dict(
        database_url="postgresql+asyncpg://t:t@localhost:5432/t",
        llm_base_url="http://llm.test/v1",
        llm_api_key="k",
        llm_model="m",
        jwt_secret=SECRET,
    )
    base.update(overrides)
    return Settings(_env_file=None, **base)


def make_token(claims: dict, key: str = SECRET) -> str:
    return jwt.encode(claims, key, algorithm="HS256")


def test_valid_token_returns_user():
    exp = datetime.now(timezone.utc) + timedelta(minutes=5)
    token = make_token({"sub": "42", "role": "USER", "exp": exp})
    claims = decode_token(token, settings(jwt_role_claim="role"))
    assert claims.user_id == "42"
    assert claims.role == "USER"


def test_numeric_custom_claim_is_stringified():
    # PyJWT خودش sub غیر رشته‌ای را رد می‌کند؛ claim سفارشی عددی مجاز است.
    token = make_token({"userId": 42})
    assert decode_token(token, settings(jwt_user_id_claim="userId")).user_id == "42"


def test_expired_token_rejected():
    exp = datetime.now(timezone.utc) - timedelta(minutes=1)
    with pytest.raises(AuthError):
        decode_token(make_token({"sub": "42", "exp": exp}), settings())


def test_wrong_signature_rejected():
    with pytest.raises(AuthError):
        decode_token(make_token({"sub": "42"}, key="other-secret"), settings())


def test_malformed_token_rejected():
    for token in ("", "not-a-token", "a.b.c"):
        with pytest.raises(AuthError):
            decode_token(token, settings())


def test_missing_user_claim_rejected():
    with pytest.raises(AuthError):
        decode_token(make_token({"role": "USER"}), settings())


def test_custom_user_claim():
    token = make_token({"userId": "77"})
    assert decode_token(token, settings(jwt_user_id_claim="userId")).user_id == "77"


def test_unconfigured_secret_rejected():
    with pytest.raises(AuthError):
        decode_token(make_token({}), settings(jwt_secret=None))


def test_issuer_and_audience_checked():
    exp = datetime.now(timezone.utc) + timedelta(minutes=5)
    token = make_token({"sub": "1", "iss": "beauty", "aud": "ai", "exp": exp})
    assert decode_token(token, settings(jwt_issuer="beauty", jwt_audience="ai")).user_id == "1"
    with pytest.raises(AuthError):
        decode_token(token, settings(jwt_issuer="other", jwt_audience="ai"))
    with pytest.raises(AuthError):
        decode_token(token, settings(jwt_audience="other"))


def test_guest_from_header():
    class Req:
        headers = {"X-Guest-Session-Id": "abc"}
        cookies = {}

    ident = resolve_guest(Req(), Response())
    assert ident.is_guest
    assert ident.guest_session_id == "abc"


def test_guest_from_cookie():
    class Req:
        headers = {}
        cookies = {"bb_guest_session": "from-cookie"}

    ident = resolve_guest(Req(), Response())
    assert ident.guest_session_id == "from-cookie"


def test_new_guest_generated():
    class Req:
        headers = {}
        cookies = {}

    ident = resolve_guest(Req(), Response())
    assert ident.is_guest
    assert ident.guest_session_id
    assert len(ident.guest_session_id) >= 16
