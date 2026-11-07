from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

_engine = None
SessionLocal: async_sessionmaker[AsyncSession] | None = None


def _init_engine() -> None:
    """موتور تنبل ساخته می‌شود تا import بدون دیتابیس هم ممکن باشد (تست)."""
    global _engine, SessionLocal
    if SessionLocal is not None:
        return
    _settings = get_settings()
    _engine = create_async_engine(
        _settings.database_url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=10,
    )
    SessionLocal = async_sessionmaker(
        _engine,
        expire_on_commit=False,
    )


async def get_session() -> AsyncIterator[AsyncSession]:
    """Dependency برای FastAPI: Depends(get_session)"""
    _init_engine()
    assert SessionLocal is not None
    async with SessionLocal() as session:
        yield session


async def dispose_engine() -> None:
    global _engine, SessionLocal
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    SessionLocal = None
