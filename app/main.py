from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routes.chat import router as chat_router
from app.api.v1.routes.listings import router as listings_router
from app.api.v1.routes.knowledge import router as knowledge_router
from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.spring_boot import router as spring_boot_router
from app.core.config import get_settings
from app.database.session import dispose_engine
from app.integrations.spring_boot.client import SpringBootClient
from app.ai.llm import FakeLLMClient, LLMClient, create_llm_client
from app.tools.base import ToolRegistry
from app.tools.registry import default_registry


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()

    spring_boot_client = SpringBootClient(
        base_url=settings.spring_boot_base_url,
        timeout=settings.spring_boot_timeout,
    )
    if settings.llm_use_fake:
        llm_client: LLMClient = FakeLLMClient()
    else:
        llm_client: LLMClient = create_llm_client()
    tool_registry: ToolRegistry = default_registry(
        include_listing_tools=settings.enable_listing_tools,
    )

    app.state.spring_boot_client = spring_boot_client
    app.state.llm_client = llm_client
    app.state.tool_registry = tool_registry

    try:
        yield
    finally:
        await spring_boot_client.aclose()
        close_llm = getattr(llm_client, "aclose", None)
        if close_llm:
            await close_llm()
        await dispose_engine()


app = FastAPI(
    title="Beauty-RAG API",
    version="0.2.0",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Guest-Session-Id"],
)

app.include_router(health_router)
app.include_router(spring_boot_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(listings_router, prefix="/api/v1")
app.include_router(knowledge_router, prefix="/api/v1")
