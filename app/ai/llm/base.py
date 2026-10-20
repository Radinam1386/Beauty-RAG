from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

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


class LLMClient(ABC):
    @abstractmethod
    async def chat(self, messages: list[Message], **opts: Any) -> LLMResponse: ...