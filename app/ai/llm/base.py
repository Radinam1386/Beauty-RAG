from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

Message = dict[str, Any]


@dataclass(frozen=True)
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0


@dataclass(frozen=True)
class LLMResponse:
    content: str | None
    usage: Usage = field(default_factory=Usage)
    finish_reason: str | None = None
    model: str | None = None
    latency_ms: int = 0
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    listings: list[dict[str, Any]] = field(default_factory=list)
    sources: list[dict[str, Any]] = field(default_factory=list)


class LLMClient(ABC):
    @abstractmethod
    async def chat(self, messages: list[Message], **opts: Any) -> LLMResponse: ...

    async def stream_chat(self, messages: list[Message], **opts: Any) -> AsyncIterator[str]:
        """اگر ارائه‌دهنده streaming نداشت، پاسخ کامل را یک‌تکه می‌فرستد."""
        response = await self.chat(messages, **opts)
        if response.content:
            yield response.content
