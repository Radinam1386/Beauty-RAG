"""آمادگی اتصال به سایت اصلی: JWKS، اولویت کلیدها و پیشوند API."""

import jwt
import pytest

from app.auth.jwt import AuthError, decode_token
from app.core.config import Settings

SECRET = "integration-secret"


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


class FakeJwksClient:
    def __init__(self, key: str) -> None:
        self.key = key

    def get_signing_key_from_jwt(self, token: str):
        class Key:
            pass

        k = Key()
        k.key = self.key
        return k


def test_jwks_url_is_used(monkeypatch):
    monkeypatch.setattr(
        "app.auth.jwt._jwks_client", lambda url: FakeJwksClient(SECRET)
    )
    token = make_token({"sub": "9"})
    claims = decode_token(
        token, settings(jwt_jwks_url="https://login.example/.well-known/jwks.json")
    )
    assert claims.user_id == "9"


def test_jwks_takes_priority_over_shared_secret(monkeypatch):
    other_key = "different-key"
    monkeypatch.setattr(
        "app.auth.jwt._jwks_client", lambda url: FakeJwksClient(other_key)
    )
    token = make_token({"sub": "9"})  # امضا با SECRET، نه کلید JWKS
    with pytest.raises(AuthError):
        decode_token(token, settings(jwt_jwks_url="https://login.example/jwks"))


def test_jwks_failure_is_auth_error(monkeypatch):
    class Broken:
        def get_signing_key_from_jwt(self, token):
            raise jwt.PyJWKClientError("unknown kid")

    monkeypatch.setattr("app.auth.jwt._jwks_client", lambda url: Broken())
    with pytest.raises(AuthError):
        decode_token(
            make_token({"sub": "9"}), settings(jwt_jwks_url="https://login.example/jwks")
        )


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("/api/v1", "/api/v1"),
        ("api/v2/", "/api/v2"),
        ("/", ""),
        ("", ""),
        ("  /ai/api/  ", "/ai/api"),
    ],
)
def test_api_prefix_is_normalized(raw, expected):
    assert settings(api_prefix=raw).api_prefix_clean == expected


def test_default_prefix_routes_are_mounted():
    from app.main import app

    paths = set(app.openapi()["paths"])
    assert "/api/v1/chat" in paths
    assert "/api/v1/conversations" in paths
    assert "/health" in paths
