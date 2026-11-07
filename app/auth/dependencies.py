from fastapi import Depends, Request, Response

from app.auth.identity import Identity, resolve_identity
from app.core.config import get_settings


def get_identity(
    request: Request,
    response: Response,
) -> Identity:
    s = get_settings()
    return resolve_identity(
        request,
        response,
        user_id_header=s.user_id_header,
        guest_session_header=s.guest_session_header,
        cookie_name=s.guest_cookie_name,
        cookie_max_age=s.guest_session_max_age,
    )


IdentityDep = Depends(get_identity)
