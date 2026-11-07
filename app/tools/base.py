"""رابط استاندارد Tool Calling — مطابق فاز ۲ سند پروژه.

هر ابزار یک نام، توضیح، JSON Schema پارامترها و یک handler دارد.
این قرارداد OpenAI-compatible است تا مستقیم به LLM وصل شود.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ToolResult:
    """خروجی اجرای یک ابزار. content معمولاً JSON رشته‌شده است."""
    content: str
    is_error: bool = False
    meta: dict[str, Any] = field(default_factory=dict)


Handler = Callable[[dict[str, Any]], Awaitable[ToolResult]]


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema
    handler: Handler

    def to_openai_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def names(self) -> list[str]:
        return list(self._tools)

    def to_openai_schemas(self) -> list[dict[str, Any]]:
        return [t.to_openai_schema() for t in self._tools.values()]

    async def dispatch(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult(
                content=f"ابزار «{name}» وجود ندارد.",
                is_error=True,
            )
        try:
            return await tool.handler(arguments)
        except Exception as exc:  # noqa: BLE001 — خطای ابزار نباید چت را بترکاند
            return ToolResult(
                content=f"اجرای ابزار «{name}» شکست خورد: {exc}",
                is_error=True,
            )
