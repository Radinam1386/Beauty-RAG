from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_session

router = APIRouter(tags=["Health"])


@router.get("/")
async def root():
    return {
        "name": "BeautyBoss AI",
        "docs": "/docs",
        "health": "/health",
        "chat": "/api/v1/conversations",
    }


@router.get("/health")
async def health(session: AsyncSession = Depends(get_session)):
    db = "ok"
    status = "ok"
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        db = f"error: {type(exc).__name__}"
        status = "degraded"
    return {
        "status": status,
        "service": "beauty-rag",
        "database": db,
    }
