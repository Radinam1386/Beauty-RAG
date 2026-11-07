from typing import Any, AsyncIterator

from app.ai.llm.base import LLMClient, LLMResponse, Message, Usage


class FakeLLMClient(LLMClient):
    """کلاینت آزمایشی: بدون اینترنت، همیشه یک جواب ثابت می‌دهد.
    اگر error داده شود، به‌جای جواب همان خطا را برمی‌گرداند.
    برای تست Tool Calling می‌توان tool_calls هم تنظیم کرد."""

    def __init__(
        self,
        reply: str = "این یک پاسخ آزمایشی است.",
        error: Exception | None = None,
        tool_calls: list[dict[str, Any]] | None = None,
    ):
        self.reply = reply
        self.error = error
        self.tool_calls = tool_calls or []
        self.last_messages: list[Message] | None = None
        self.chat_calls = 0

    async def chat(self, messages: list[Message], **opts: Any) -> LLMResponse:
        self.last_messages = messages
        self.chat_calls += 1
        if self.error:
            raise self.error
        return LLMResponse(
            content=self.reply,
            usage=Usage(prompt_tokens=10, completion_tokens=5),
            finish_reason="tool_calls" if self.tool_calls else "stop",
            model="fake-model",
            tool_calls=list(self.tool_calls),
        )

    async def stream_chat(self, messages: list[Message], **opts: Any) -> AsyncIterator[str]:
        self.last_messages = messages
        self.chat_calls += 1
        if self.error:
            raise self.error
        text = self.reply
        step = 3
        for i in range(0, len(text), step):
            yield text[i : i + step]
