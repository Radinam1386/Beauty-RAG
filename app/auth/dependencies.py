from typing import Annotated

from fastapi import Depends, HTTPException, Request, Response, status

from app.auth.identity import Identity, resolve_guest
from app.auth.jwt import AuthError, decode_token
from app.core.config import get_settings


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_identity(request: Request, response: Response) -> Identity:
    """توکن معتبر ← کاربر؛ بدون توکن ← مهمان؛ توکن خراب ← ۴۰۱."""
    settings = get_settings()
    header = request.headers.get("Authorization")
    if header:
        scheme, _, token = header.partition(" ")
        if scheme.lower() != "bearer" or not token.strip():
            raise _unauthorized("ساختار هدر Authorization درست نیست")
        try:
            claims = decode_token(token.strip(), settings)
        except AuthError as exc:
            raise _unauthorized(str(exc)) from exc
        return Identity(
            owner_type="user",
            external_user_id=claims.user_id,
            guest_session_id=None,
            role=claims.role,
        )

    return resolve_guest(
        request,
        response,
        guest_session_header=settings.guest_session_header,
        cookie_name=settings.guest_cookie_name,
        cookie_max_age=settings.guest_session_max_age,
    )


def require_user(identity: Annotated[Identity, Depends(get_identity)]) -> Identity:
    """برای endpointهایی که فقط کاربر لاگین‌شده حق دارد."""
    if identity.is_guest:
        raise _unauthorized("برای این بخش باید وارد حساب کاربری شوید")
    return identity


IdentityDep = Annotated[Identity, Depends(get_identity)]
CurrentUserDep = Annotated[Identity, Depends(require_user)]
