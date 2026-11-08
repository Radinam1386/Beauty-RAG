"""هویت درخواست: کاربر لاگین‌شده یا مهمان.

کاربر لاگین‌شده: JWT در هدر ``Authorization: Bearer ...`` (در dependencies).
مهمان: هدر X-Guest-Session-Id یا کوکی bb_guest_session؛ اگر نبود نشست مهمان جدید.
هیچ‌وقت user_id از هدر/بدنه/کوئری خوانده نمی‌شود؛ فقط از توکن.
"""

import uuid
from dataclasses import dataclass

from fastapi import Request, Response

MAX_ID_LEN = 64


@dataclass(frozen=True)
class Identity:
    owner_type: str  # 'guest' | 'user'
    external_user_id: str | None
    guest_session_id: str | None
    role: str | None = None

    @property
    def is_guest(self) -> bool:
        return self.owner_type == "guest"

    @property
    def is_user(self) -> bool:
        return self.owner_type == "user"


def _clean(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    return value[:MAX_ID_LEN] if value else None


def resolve_guest(
    request: Request,
    response: Response,
    *,
    guest_session_header: str = "X-Guest-Session-Id",
    cookie_name: str = "bb_guest_session",
    cookie_max_age: int = 60 * 60 * 24 * 30,
) -> Identity:
    guest_id = _clean(request.headers.get(guest_session_header))
    if not guest_id:
        guest_id = _clean(request.cookies.get(cookie_name))
    if not guest_id:
        guest_id = uuid.uuid4().hex
        response.set_cookie(
            key=cookie_name,
            value=guest_id,
            max_age=cookie_max_age,
            httponly=True,
            samesite="lax",
        )

    response.headers[guest_session_header] = guest_id
    return Identity(
        owner_type="guest",
        external_user_id=None,
        guest_session_id=guest_id,
    )
