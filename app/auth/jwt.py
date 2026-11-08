"""اعتبارسنجی JWT صادرشده توسط سایت اصلی (Spring Boot / Keycloak).

سرویس AI فقط توکن را چک می‌کند؛ لاگین/ثبت‌نام/صدور توکن دست سایت اصلی است.
سه حالت پشتیبانی می‌شود (به ترتیب اولویت):
1. ``JWT_JWKS_URL`` — کلید عمومی از JWKS گرفته و کش می‌شود (مناسب Keycloak/Spring).
2. ``JWT_PUBLIC_KEY`` — کلید عمومی ثابت (RS*).
3. ``JWT_SECRET`` — کلید مشترک (HS*).
"""

from dataclasses import dataclass

import jwt
from jwt import PyJWKClient

from app.core.config import Settings

MAX_USER_ID_LEN = 64
MAX_ROLE_LEN = 32

# کش کلاینت JWKS به ازای URL (خودِ کلاینت، کلیدها را کش می‌کند)
_jwks_clients: dict[str, PyJWKClient] = {}


class AuthError(Exception):
    """توکن نامعتبر، منقضی یا تنظیم‌نشده است."""


@dataclass(frozen=True)
class TokenClaims:
    user_id: str
    role: str | None = None


def _jwks_client(url: str) -> PyJWKClient:
    client = _jwks_clients.get(url)
    if client is None:
        # lifespan: هر چند دقیقه یک بار کلیدها تازه می‌شوند (چرخش کلید Keycloak)
        client = PyJWKClient(url, cache_keys=True, lifespan=300)
        _jwks_clients[url] = client
    return client


def _signing_key(token: str, settings: Settings) -> str:
    if settings.jwt_jwks_url:
        try:
            return _jwks_client(settings.jwt_jwks_url).get_signing_key_from_jwt(token).key
        except jwt.PyJWKClientError as exc:
            raise AuthError("کلید امضای توکن پیدا نشد") from exc

    if settings.jwt_public_key:
        # کلید عمومی معمولاً در env یک‌خطی ذخیره می‌شود
        return settings.jwt_public_key.replace("\\n", "\n")
    if settings.jwt_secret:
        return settings.jwt_secret.get_secret_value()
    raise AuthError("JWT روی سرویس تنظیم نشده است")


def decode_token(token: str, settings: Settings) -> TokenClaims:
    """توکن را چک می‌کند و user_id/role را برمی‌گرداند؛ در خطا AuthError."""
    if not settings.jwt_algorithm:
        raise AuthError("الگوریتم JWT تنظیم نشده است")

    try:
        claims = jwt.decode(
            token,
            _signing_key(token, settings),
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience or None,
            issuer=settings.jwt_issuer or None,
            options={
                "verify_aud": bool(settings.jwt_audience),
                "verify_iss": bool(settings.jwt_issuer),
            },
        )
    except jwt.InvalidTokenError as exc:  # شامل منقضی، امضای غلط و ساختار خراب
        raise AuthError("توکن معتبر نیست") from exc

    claim = settings.jwt_user_id_claim or "sub"
    raw = claims.get(claim)
    if raw is None or not str(raw).strip():
        raise AuthError(f"claim «{claim}» در توکن نیست")

    role: str | None = None
    if settings.jwt_role_claim:
        role_value = claims.get(settings.jwt_role_claim)
        if role_value is not None:
            role = str(role_value)[:MAX_ROLE_LEN]

    return TokenClaims(user_id=str(raw).strip()[:MAX_USER_ID_LEN], role=role)
