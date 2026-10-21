
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.routes.health import router as health_router
from app.core.config import get_settings
from app.integrations.spring_boot.client import SpringBootClient


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()

    spring_boot_client = SpringBootClient(
        base_url=settings.spring_boot_base_url,
        timeout=settings.spring_boot_timeout,
    )

    app.state.spring_boot_client = spring_boot_client

    try:
        yield
    finally:
        await spring_boot_client.aclose()


app = FastAPI(
    title="Beauty-RAG API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health_router)
