"""محدودیت نرخ درخواست و بودجه روزانه توکن.

نسخه فعلی در حافظه است؛ فقط با یک worker درست کار می‌کند.
برای چند worker فقط همین فایل را با Redis عوض کن.
"""

import logging
import time
from collections import defaultdict, deque
from datetime import datetime, timezone

from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.identity import Identity
from app.core.config import Settings
from app.database.models import DailyUsage

logger = logging.getLogger(__name__)

DAY_SECONDS = 60 * 60 * 24
MINUTE_SECONDS = 60


class RateLimiter:
    """پنجرهٔ لغزان: برای هر کلید، زمان درخواست‌های ۲۴ ساعت اخیر."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def reset(self) -> None:
        self._hits.clear()

    def hit(
        self,
        key: str,
        *,
        per_minute: int,
        per_day: int,
        now: float | None = None,
    ) -> int:
        """یک درخواست ثبت می‌کند؛ اگر مجاز بود ۰، وگرنه ثانیه‌های انتظار."""
        ts = time.monotonic() if now is None else now
        hits = self._hits[key]

        while hits and hits[0] <= ts - DAY_SECONDS:
            hits.popleft()

        if per_day > 0 and len(hits) >= per_day:
            return max(1, int(DAY_SECONDS - (ts - hits[0])))

        if per_minute > 0:
            recent = [t for t in hits if t > ts - MINUTE_SECONDS]
            if len(recent) >= per_minute:
                # قدیمی‌ترین درخواستی که جای خالی را آزاد می‌کند
                slot = recent[len(recent) - per_minute]
                return max(1, int(MINUTE_SECONDS - (ts - slot)))

        hits.append(ts)
        return 0


rate_limiter = RateLimiter()


def client_ip(request: Request, settings: Settings) -> str:
    """IP کاربر؛ X-Forwarded-For فقط وقتی پروکسی صراحتاً تأیید شده باشد."""
    if settings.trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for", "")
        first = forwarded.split(",")[0].strip()
        if first:
            return first[:64]
    host = request.client.host if request.client else "unknown"
    return host[:64]


def rate_limit_key(
    request: Request,
    identity: Identity,
    settings: Settings,
) -> tuple[str, int, int]:
    if identity.is_user:
        return (
            f"user:{identity.external_user_id}",
            settings.user_rate_per_minute,
            settings.user_rate_per_day,
        )
    return (
        f"ip:{client_ip(request, settings)}",
        settings.anonymous_rate_per_minute,
        settings.anonymous_rate_per_day,
    )


def enforce_rate_limit(request: Request, identity: Identity, settings: Settings) -> None:
    key, per_minute, per_day = rate_limit_key(request, identity, settings)
    retry_after = rate_limiter.hit(key, per_minute=per_minute, per_day=per_day)
    if retry_after:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="تعداد پیام‌ها زیاد است. لطفاً کمی بعد دوباره تلاش کنید.",
            headers={"Retry-After": str(retry_after)},
        )


class DailyBudget:
    """مصرف روزانه LLM در PostgreSQL؛ با ری‌استارت صفر نمی‌شود."""

    def __init__(self, session: AsyncSession, limit: int) -> None:
        self.session = session
        self.limit = limit

    @staticmethod
    def _today():
        return datetime.now(timezone.utc).date()

    async def used_tokens(self) -> int:
        stmt = select(DailyUsage.total_tokens).where(DailyUsage.day == self._today())
        return int((await self.session.execute(stmt)).scalar_one_or_none() or 0)

    async def check(self) -> None:
        if self.limit <= 0:
            return
        try:
            used = await self.used_tokens()
        except SQLAlchemyError:
            # نبودن جدول/دیتابیس نباید کل چت را بخواباند؛ فقط لاگ می‌کنیم
            logger.warning("daily usage read failed; skipping budget check")
            return
        if used >= self.limit:
            logger.warning("daily token limit reached: %s >= %s", used, self.limit)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="سرویس موقتاً در دسترس نیست. لطفاً بعداً تلاش کنید.",
            )

    async def record(self, prompt_tokens: int = 0, completion_tokens: int = 0) -> None:
        tokens = int(prompt_tokens or 0) + int(completion_tokens or 0)
        stmt = (
            insert(DailyUsage)
            .values(day=self._today(), requests=1, total_tokens=tokens)
            .on_conflict_do_update(
                index_elements=[DailyUsage.day],
                set_={
                    "requests": DailyUsage.requests + 1,
                    "total_tokens": DailyUsage.total_tokens + tokens,
                },
            )
        )
        try:
            await self.session.execute(stmt)
            await self.session.commit()
        except SQLAlchemyError:
            await self.session.rollback()
            logger.warning("daily usage write failed", exc_info=True)
