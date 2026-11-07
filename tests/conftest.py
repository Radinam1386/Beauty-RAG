"""فیکسچرهای مشترک فاز ۲ — بدون دیتابیس واقعی و بدون LLM واقعی."""

import os
import uuid
from datetime import datetime, timezone
from typing import Any

import pytest

# قبل از import app.main باید env آماده باشد
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("LLM_BASE_URL", "http://llm.test/v1")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_MODEL", "test-model")
os.environ.setdefault("SPRING_BOOT_BASE_URL", "http://spring.test")

from fastapi import FastAPI  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.ai.llm import FakeLLMClient, LLMClient, LLMResponse, Usage  # noqa: E402
from app.api.dependencies import (  # noqa: E402
    get_chat_service,
    get_llm_client,
    get_tool_registry,
)
from app.api.v1.routes.chat import router as chat_router  # noqa: E402
from app.auth.identity import Identity  # noqa: E402
from app.auth.dependencies import get_identity  # noqa: E402
from app.chat.repository import ChatRepository  # noqa: E402
from app.chat.service import ChatService  # noqa: E402
from app.database.models import Conversation, Message  # noqa: E402
from app.tools.base import Tool, ToolRegistry, ToolResult  # noqa: E402


class FakeChatRepository(ChatRepository):
    """حافظه‌ای، بدون SQLAlchemy. قرارداد ChatService را رعایت می‌کند."""

    def __init__(self) -> None:
        self.conversations: dict[uuid.UUID, Conversation] = {}
        self.messages: dict[uuid.UUID, list[Message]] = {}
        self._msg_seq = 1

    async def create_conversation(self, identity: Identity, title: str | None = None) -> Conversation:
        conv = Conversation(
            id=uuid.uuid4(),
            owner_type=identity.owner_type,
            external_user_id=identity.external_user_id,
            guest_session_id=identity.guest_session_id,
            title=title,
            status="active",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.conversations[conv.id] = conv
        self.messages[conv.id] = []
        return conv

    async def get_conversation(self, identity: Identity, conversation_id: uuid.UUID, *, include_archived: bool = False) -> Conversation | None:
        conv = self.conversations.get(conversation_id)
        if conv is None:
            return None
        if identity.is_user:
            ok = conv.owner_type == "user" and conv.external_user_id == identity.external_user_id
        else:
            ok = conv.owner_type == "guest" and conv.guest_session_id == identity.guest_session_id
        if not ok:
            return None
        if not include_archived and conv.status != "active":
            return None
        return conv

    async def list_conversations(
        self,
        identity: Identity,
        page: int = 1,
        page_size: int = 20,
        status: str = "active",
    ) -> tuple[list[Conversation], int]:
        mine = []
        for conv in self.conversations.values():
            if identity.is_user:
                ok = conv.owner_type == "user" and conv.external_user_id == identity.external_user_id
            else:
                ok = conv.owner_type == "guest" and conv.guest_session_id == identity.guest_session_id
            if ok and conv.status == status:
                mine.append(conv)
        mine.sort(key=lambda c: c.updated_at, reverse=True)
        total = len(mine)
        offset = (page - 1) * page_size
        return mine[offset : offset + page_size], total

    async def add_message(self, conversation: Conversation, **fields: Any) -> Message:
        msg = Message(
            id=self._msg_seq,
            conversation_id=conversation.id,
            created_at=datetime.now(timezone.utc),
            **fields,
        )
        self._msg_seq += 1
        self.messages[conversation.id].append(msg)
        conversation.updated_at = datetime.now(timezone.utc)
        return msg

    async def touch_conversation(self, conversation: Conversation, title: str | None = None) -> None:
        if title is not None:
            conversation.title = title
        conversation.updated_at = datetime.now(timezone.utc)

    async def list_messages(
        self,
        conversation: Conversation,
        limit: int | None = None,
        order_desc: bool = False,
    ) -> list[Message]:
        rows = list(self.messages.get(conversation.id, []))
        if order_desc:
            rows = list(reversed(rows))
            if limit is not None:
                rows = rows[:limit]
        else:
            if limit is not None:
                rows = rows[-limit:]
        return rows

    async def count_messages(self, conversation: Conversation) -> int:
        return len(self.messages.get(conversation.id, []))

    async def archive_conversation(self, conversation: Conversation) -> None:
        conversation.status = "archived"

    async def delete_conversation(self, conversation: Conversation) -> None:
        self.conversations.pop(conversation.id, None)
        self.messages.pop(conversation.id, None)

    async def commit(self) -> None:
        return None

    async def refresh(self, obj: Any) -> None:
        return None


def make_identity(user: bool = False, key: str = "u1") -> Identity:
    if user:
        return Identity(owner_type="user", external_user_id=key, guest_session_id=None)
    return Identity(owner_type="guest", external_user_id=None, guest_session_id=key)


@pytest.fixture
def fake_repo() -> FakeChatRepository:
    return FakeChatRepository()


@pytest.fixture
def fake_llm() -> FakeLLMClient:
    return FakeLLMClient(reply="پاسخ آزمایشی دستیار.")


@pytest.fixture
def guest() -> Identity:
    return make_identity(user=False, key="guest-1")


@pytest.fixture
def user() -> Identity:
    return make_identity(user=True, key="user-1")


@pytest.fixture
def app(
    fake_repo: FakeChatRepository,
    fake_llm: FakeLLMClient,
    guest: Identity,
) -> FastAPI:
    test_app = FastAPI()
    test_app.include_router(chat_router, prefix="/api/v1")
    service = ChatService(repository=fake_repo, llm=fake_llm, tools=None)

    test_app.dependency_overrides[get_identity] = lambda: guest
    test_app.dependency_overrides[get_chat_service] = lambda: service
    test_app.dependency_overrides[get_llm_client] = lambda: fake_llm
    test_app.dependency_overrides[get_tool_registry] = lambda: ToolRegistry()
    return test_app


@pytest.fixture
async def client(app: FastAPI):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
