"""Conversation Manager — فاز ۲ و ۳.

وظایف:
- ساخت پیام‌ها از تاریخچه (حداکثر ۸ پیام)
- افزودن prompt سیستمی فارسی بر اساس ابزارهای فعال
- حلقه Tool Calling استاندارد و جمعآوری آگهیها
- Streaming در صورت پشتیبانی مدل
"""

import json
import logging
from dataclasses import replace
from typing import Any, AsyncIterator

from app.ai.llm import LLMClient, LLMResponse, Message
from app.ai.memory.manager import build_messages
from app.ai.prompts.system import build_system_prompt
from app.tools.base import ToolRegistry

logger = logging.getLogger(__name__)

EMPTY_REPLY = "متأسفم، نتوانستم پاسخی آماده کنم. لطفاً دوباره امتحان کنید."
MAX_TOOL_ROUNDS = 3


class ConversationManager:
    def __init__(
        self,
        llm: LLMClient,
        tools: ToolRegistry | None = None,
        max_history: int = 8,
        system_prompt: str | None = None,
    ) -> None:
        self.llm = llm
        self.tools = tools
        self.max_history = max_history
        if system_prompt is None:
            has_listings = bool(tools and "search_listings" in tools.names())
            has_create = bool(tools and "prepare_listing_request" in tools.names())
            has_rag = bool(tools and "search_knowledge" in tools.names())
            system_prompt = build_system_prompt(
                listing_search=has_listings, listing_create=has_create, rag=has_rag
            )
        self.system_prompt = system_prompt

    def _prepare(self, history: list[Message]) -> list[Message]:
        return build_messages(
            history,
            system_prompt=self.system_prompt,
            max_messages=self.max_history,
        )

    def _tool_schemas(self) -> list[dict] | None:
        if not self.tools or not self.tools.names():
            return None
        return self.tools.to_openai_schemas()

    async def _run_tools(self, response: LLMResponse) -> tuple[list[Message], list[dict[str, Any]]]:
        """اجرای tool_calls و برگرداندن پیامهای tool + آگهیهای جمعشده."""
        if not response.tool_calls or not self.tools:
            return [], [], []
        tool_messages: list[Message] = []
        listings: list[dict[str, Any]] = []
        sources: list[dict[str, Any]] = []
        for call in response.tool_calls:
            fn = call.get("function") or {}
            name = fn.get("name") or call.get("name") or ""
            raw_args = fn.get("arguments", call.get("arguments", "{}"))
            try:
                args = json.loads(raw_args) if isinstance(raw_args, str) else dict(raw_args or {})
            except (TypeError, ValueError):
                args = {}
            result = await self.tools.dispatch(name, args)
            call_id = call.get("id") or f"call_{name}"
            tool_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": result.content,
                }
            )
            meta = result.meta if isinstance(result.meta, dict) else {}
            if name in ("search_listings", "get_listing_details"):
                found = meta.get("listings") or []
                listings.extend(found)
            if name in ("search_knowledge", "get_knowledge_article"):
                found = meta.get("sources") or []
                sources.extend(found)
        return tool_messages, listings, sources

    async def reply(self, history: list[Message], **opts) -> LLMResponse:
        messages = self._prepare(history)
        schemas = self._tool_schemas()
        opts.setdefault("max_tokens", 2048)
        opts.setdefault("temperature", 0.7)
        response = (
            await self.llm.chat(messages, tools=schemas, **opts)
            if schemas
            else await self.llm.chat(messages, **opts)
        )

        rounds = 0
        collected: list[dict[str, Any]] = []
        collected_sources: list[dict[str, Any]] = []
        while response.tool_calls and self.tools and rounds < MAX_TOOL_ROUNDS:
            rounds += 1
            assistant_with_tools: Message = {
                "role": "assistant",
                "content": response.content or "",
                "tool_calls": response.tool_calls,
            }
            tool_msgs, listings, sources = await self._run_tools(response)
            collected.extend(listings)
            collected_sources.extend(sources)
            if not tool_msgs:
                break
            messages = messages + [assistant_with_tools] + tool_msgs
            response = (
                await self.llm.chat(messages, tools=schemas, **opts)
                if schemas
                else await self.llm.chat(messages, **opts)
            )

        if not response.content:
            response = replace(response, content=EMPTY_REPLY)
        if collected:
            response = replace(response, listings=collected)
        if collected_sources:
            response = replace(response, sources=collected_sources)
        return response

    async def stream(self, history: list[Message], **opts) -> AsyncIterator[str]:
        """استریم پاسخ. اگر ابزار فعال است، اول دور غیراستریم برای tool_call."""
        messages = self._prepare(history)
        schemas = self._tool_schemas()
        opts.setdefault("max_tokens", 2048)
        opts.setdefault("temperature", 0.7)

        if schemas:
            response = await self.llm.chat(messages, tools=schemas, **opts)
            rounds = 0
            while response.tool_calls and self.tools and rounds < MAX_TOOL_ROUNDS:
                rounds += 1
                assistant_with_tools: Message = {
                    "role": "assistant",
                    "content": response.content or "",
                    "tool_calls": response.tool_calls,
                }
                tool_msgs, _listings, _sources = await self._run_tools(response)
                if not tool_msgs:
                    break
                messages = messages + [assistant_with_tools] + tool_msgs
                response = await self.llm.chat(messages, tools=schemas, **opts)
            if response.content:
                yield response.content
            return

        async for delta in self.llm.stream_chat(messages, **opts):
            if delta:
                yield delta
