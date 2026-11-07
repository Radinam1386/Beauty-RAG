from typing import Annotated

from fastapi import Depends, Request

from app.ai.llm import LLMClient
from app.auth.dependencies import get_identity
from app.auth.identity import Identity
from app.chat.repository import ChatRepository
from app.chat.service import ChatService
from app.core.config import get_settings
from app.database.session import get_session
from app.integrations.spring_boot.client import SpringBootClient
from app.listings.service import ListingService
from app.tools.base import ToolRegistry
from sqlalchemy.ext.asyncio import AsyncSession


def get_spring_boot_client(request: Request) -> SpringBootClient:
    return request.app.state.spring_boot_client


def get_llm_client(request: Request) -> LLMClient:
    return request.app.state.llm_client


def get_tool_registry(request: Request) -> ToolRegistry:
    return request.app.state.tool_registry


def get_chat_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ChatRepository:
    return ChatRepository(session)


def get_chat_service(
    repository: Annotated[ChatRepository, Depends(get_chat_repository)],
    llm: Annotated[LLMClient, Depends(get_llm_client)],
    identity: Annotated[Identity, Depends(get_identity)],
    spring_boot_client: Annotated[SpringBootClient, Depends(get_spring_boot_client)],
    settings: Annotated[object, Depends(get_settings)],
) -> ChatService:
    from app.tools.registry import default_registry
    s = get_settings()
    listing_service = ListingService(client=spring_boot_client)
    tools = default_registry(
        include_listing_tools=s.enable_listing_tools,
        include_knowledge_tools=s.enable_knowledge_tools,
        identity=identity,
        listing_service=listing_service,
    )
    return ChatService(
        repository=repository,
        llm=llm,
        tools=tools,
        listing_service=listing_service,
    )


SpringBootDep = Annotated[SpringBootClient, Depends(get_spring_boot_client)]
LLMDep = Annotated[LLMClient, Depends(get_llm_client)]
ToolsDep = Annotated[ToolRegistry, Depends(get_tool_registry)]
ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]
IdentityDep = Annotated[Identity, Depends(get_identity)]
