"""منطق چت: مالکیت، ذخیره پیام، فراخوانی مدل و حافظه.

این سرویس بین API و LLM می‌نشیند؛ endpointها نباید مستقیم با SQLAlchemy کار کنند.
"""

import json
import logging
import re
import time
import uuid
from dataclasses import dataclass
from typing import Any

from app.ai.llm import LLMClient, LLMResponse
from app.ai.llm.errors import LLMError
from app.ai.memory.manager import MAX_HISTORY
from app.ai.orchestration.conversation import ConversationManager
from app.auth.identity import Identity
from app.chat.exceptions import (
    ConversationAccessError,
    ConversationNotFound,
    EmptyMessageError,
    MessageTooLongError,
)
from app.chat.repository import ChatRepository
from app.core.config import get_settings
from app.integrations.spring_boot.client import SpringBootError
from app.listings.service import ListingService
from app.database.models import Conversation, Message
from app.tools.base import ToolRegistry

logger = logging.getLogger(__name__)


def _append_note(history: list[dict], note: str) -> list[dict]:
    """شواهد (آگهی/منبع) را به آخرین پیام کاربر می‌چسباند."""
    if not history:
        return [{"role": "user", "content": note}]
    out = [dict(m) for m in history]
    last = out[-1]
    out[-1] = {"role": "user", "content": f"{last.get('content') or ''}\n\n{note}"}
    return out


@dataclass(frozen=True)
class ChatReply:
    """پاسخ یک‌مرحله‌ای (بدون ذخیره) برای مهمان."""

    content: str
    model: str | None
    listings: list
    sources: list
    llm: LLMResponse


@dataclass(frozen=True)
class SendResult:
    conversation: Conversation
    user_message: Message
    assistant_message: Message
    llm: LLMResponse
    listings: list = None
    sources: list = None


class ChatService:
    def __init__(
        self,
        repository: ChatRepository,
        llm: LLMClient,
        tools: ToolRegistry | None = None,
        listing_service: ListingService | None = None,
    ) -> None:
        self.repo = repository
        self.llm = llm
        self.tools = tools
        self.listing_service = listing_service or ListingService()
        self.settings = get_settings()
        self.listing_intent = re.compile(
            r"(آگهی|agahi|سالن|آرایشگاه|ونک|سعادت|جستجوی آگهی|دنبال|پیدا کن|رنگ مو|میکاپ|ناخن|کاشت|مژه|لیفت)"
        )

    async def create_conversation(self, identity: Identity, title: str | None = None) -> Conversation:
        title = (title or "").strip() or None
        if title and len(title) > 200:
            title = title[:200]
        return await self.repo.create_conversation(identity, title=title)

    async def list_conversations(
        self,
        identity: Identity,
        page: int = 1,
        page_size: int | None = None,
    ) -> tuple[list[Conversation], int]:
        s = self.settings
        page = max(1, page)
        size = page_size or s.conversations_page_size
        size = min(max(1, size), s.conversations_max_page_size)
        return await self.repo.list_conversations(identity, page=page, page_size=size)

    async def get_conversation(self, identity: Identity, conversation_id: uuid.UUID) -> Conversation:
        conv = await self.repo.get_conversation(identity, conversation_id)
        if conv is None:
            # ۴۰۴ یکسان برای «نیست» و «مالکیت ندارد» تا وجود گفتگوی دیگران لو نرود
            raise ConversationNotFound(str(conversation_id))
        return conv

    async def get_messages(
        self,
        identity: Identity,
        conversation_id: uuid.UUID,
        limit: int | None = None,
    ) -> list[Message]:
        conv = await self.get_conversation(identity, conversation_id)
        return await self.repo.list_messages(conv, limit=limit, order_desc=False)

    async def delete_conversation(self, identity: Identity, conversation_id: uuid.UUID) -> None:
        conv = await self.get_conversation(identity, conversation_id)
        await self.repo.archive_conversation(conv)

    def _validate_content(self, content: str) -> str:
        text = (content or "").strip()
        if not text:
            raise EmptyMessageError()
        if len(text) > self.settings.chat_max_message_chars:
            raise MessageTooLongError()
        return text

    def _title_from_text(self, text: str) -> str:
        clean = " ".join(text.split())
        return clean[:50] + ("…" if len(clean) > 50 else "")

    async def _history_for_model(self, conversation: Conversation) -> list[dict]:
        """پیام ذخیره‌شدهٔ تازه و تاریخچه، هر کدام فقط یک بار."""
        limit = max(2, self.settings.chat_history_limit)
        recent = await self.repo.list_messages(conversation, limit=limit, order_desc=False)
        history = [
            {"role": m.role, "content": m.content or ""}
            for m in recent
            if m.role in ("user", "assistant") and m.content
        ]
        # برش نهایی به اندازه پنجره
        history = history[-limit:]
        while history and history[0]["role"] != "user":
            history.pop(0)
        return history

    async def _augment(
        self, history: list[dict], text: str
    ) -> tuple[list[dict], list, list]:
        """آگهی/منابع مرتبط را به پیام کاربر اضافه می‌کند؛ (تاریخچه، آگهی‌ها، منابع)."""
        listings: list = []
        sources: list = []
        # اگر ابزار جستجو فعال است، نتیجه از خود ابزار می‌آید تا با کارت‌های UI یکی باشد.
        has_listing_tool = bool(self.tools and "search_listings" in self.tools.names())
        if self.listing_intent.search(text) and not has_listing_tool:
            try:
                listings = await self.listing_service.search(text)
            except SpringBootError:
                logger.warning("live listing search failed")
                listings = []
            if listings:
                history = _append_note(
                    history,
                    "[نتایج جستجوی آگهی سایت BeautyBoss — فقط از این نتایج استفاده کن، "
                    "قیمت و لینک را از همین‌ها بگو و آگهی نساز]\n"
                    + json.dumps(listings, ensure_ascii=False),
                )
        return history, listings, sources

    async def reply_anonymous(self, content: str) -> ChatReply:
        """پاسخ یک‌مرحله‌ای مهمان: هیچ چیز در دیتابیس ذخیره نمی‌شود."""
        text = self._validate_content(content)
        history, listings, sources = await self._augment(
            [{"role": "user", "content": text}], text
        )
        manager = ConversationManager(
            llm=self.llm,
            tools=self.tools,
            max_history=self.settings.chat_history_limit,
        )
        try:
            response = await manager.reply(history)
        except LLMError:
            logger.exception("LLM failed for anonymous chat")
            raise
        return ChatReply(
            content=response.content or "",
            model=response.model,
            listings=listings or list(response.listings),
            sources=sources or list(response.sources),
            llm=response,
        )

    async def send_message(
        self,
        identity: Identity,
        conversation_id: uuid.UUID,
        content: str,
    ) -> SendResult:
        text = self._validate_content(content)
        conv = await self.get_conversation(identity, conversation_id)

        user_msg = await self.repo.add_message(
            conv,
            role="user",
            content=text,
        )
        # عنوان خودکار از اولین پیام کاربر
        new_title = conv.title or self._title_from_text(text)
        await self.repo.touch_conversation(conv, title=new_title)
        await self.repo.commit()
        await self.repo.refresh(user_msg)
        await self.repo.refresh(conv)

        history = await self._history_for_model(conv)
        history, pre_listings, pre_sources = await self._augment(history, text)
        manager = ConversationManager(
            llm=self.llm,
            tools=self.tools,
            max_history=self.settings.chat_history_limit,
        )

        start = time.perf_counter()
        try:
            llm_response = await manager.reply(history)
        except LLMError:
            # پیام کاربر ذخیره شده؛ خطا را به لایه API می‌دهیم تا ۵۰۲ بدهد
            logger.exception("LLM failed for conversation %s", conv.id)
            raise

        listings = pre_listings or list(llm_response.listings)
        sources = pre_sources or list(llm_response.sources)
        extra = {}
        if listings:
            extra["listings"] = listings
        if sources:
            extra["sources"] = sources
        assistant_msg = await self.repo.add_message(
            conv,
            role="assistant",
            content=llm_response.content or "",
            model=llm_response.model,
            prompt_tokens=llm_response.usage.prompt_tokens or None,
            completion_tokens=llm_response.usage.completion_tokens or None,
            latency_ms=llm_response.latency_ms or int((time.perf_counter() - start) * 1000),
            tool_calls=extra or (llm_response.tool_calls or None),
        )
        await self.repo.touch_conversation(conv)
        await self.repo.commit()
        await self.repo.refresh(assistant_msg)
        await self.repo.refresh(conv)

        return SendResult(
            conversation=conv,
            user_message=user_msg,
            assistant_message=assistant_msg,
            llm=llm_response,
            listings=listings,
            sources=sources,
        )

    async def stream_reply(self, identity: Identity, conversation_id: uuid.UUID, content: str):
        """جنریتور SSE: پیام کاربر را ذخیره می‌کند و توکن‌های مدل را می‌فرستد.

        مصرف‌کننده (route) مسئول بستن و commit نهایی است.
        """
        text = self._validate_content(content)
        conv = await self.get_conversation(identity, conversation_id)

        user_msg = await self.repo.add_message(conv, role="user", content=text)
        new_title = conv.title or self._title_from_text(text)
        await self.repo.touch_conversation(conv, title=new_title)
        await self.repo.commit()
        await self.repo.refresh(user_msg)

        history = await self._history_for_model(conv)
        manager = ConversationManager(
            llm=self.llm,
            tools=self.tools,
            max_history=self.settings.chat_history_limit,
        )

        chunks: list[str] = []
        start = time.perf_counter()
        async for delta in manager.stream(history):
            chunks.append(delta)
            yield ("delta", delta)

        content_out = "".join(chunks) or "متأسفم، نتوانستم پاسخی آماده کنم. لطفاً دوباره امتحان کنید."
        latency_ms = int((time.perf_counter() - start) * 1000)
        assistant_msg = await self.repo.add_message(
            conv,
            role="assistant",
            content=content_out,
            model=getattr(self.llm, "model", None),
            latency_ms=latency_ms,
        )
        await self.repo.touch_conversation(conv)
        await self.repo.commit()
        await self.repo.refresh(assistant_msg)
        yield ("done", assistant_msg)
