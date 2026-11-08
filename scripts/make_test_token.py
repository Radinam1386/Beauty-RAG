"""ساخت JWT تست با تنظیمات فعلی .env — فقط برای توسعه.

نمونه:
    ./env/bin/python scripts/make_test_token.py --user 42 --minutes 60
    curl -H "Authorization: Bearer $(...)" http://localhost:8000/api/v1/conversations
"""

import argparse
import time

import jwt

from app.core.config import get_settings


def build_token(user_id: str, minutes: int, role: str | None) -> str:
    settings = get_settings()
    if not settings.jwt_secret:
        raise SystemExit("JWT_SECRET در .env تنظیم نشده است")
    if settings.jwt_algorithm.upper().startswith("RS"):
        raise SystemExit("این اسکریپت فقط HS* را می‌سازد؛ برای RS256 کلید خصوصی لازم است")

    now = int(time.time())
    claims: dict = {
        settings.jwt_user_id_claim or "sub": user_id,
        "iat": now,
        "exp": now + minutes * 60,
    }
    if settings.jwt_role_claim and role:
        claims[settings.jwt_role_claim] = role
    if settings.jwt_issuer:
        claims["iss"] = settings.jwt_issuer
    if settings.jwt_audience:
        claims["aud"] = settings.jwt_audience

    return jwt.encode(
        claims,
        settings.jwt_secret.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="ساخت JWT تست")
    parser.add_argument("--user", default="42", help="شناسه کاربر (claim ی user id)")
    parser.add_argument("--minutes", type=int, default=60, help="مدت اعتبار")
    parser.add_argument("--role", default="USER", help="مقدار role (اگر JWT_ROLE_CLAIM ست شده باشد)")
    args = parser.parse_args()
    print(build_token(args.user, args.minutes, args.role))


if __name__ == "__main__":
    main()
