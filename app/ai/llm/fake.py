from typing import Any

from app.ai.llm.base import LLMClient, LLMResponse, Message, Usage


class FakeLLMClient(LLMClient):
    """کلاینت آزمایشی: بدون اینترنت، همیشه یک جواب ثابت می‌دهد.
    اگر error داده شود، به‌جای جواب همان خطا را برمی‌گرداند."""

    def __init__(self, reply: str = "این یک پاسخ آزمایشی است.", error: Exception | None = None):
        self.reply = reply
        self.error = error

    async def chat(self, messages: list[Message], **opts: Any) -> LLMResponse:
        if self.error:
            raise self.error
        return LLMResponse(
            content=self.reply,
            usage=Usage(prompt_tokens=10, completion_tokens=5),
            finish_reason="stop",
            model="fake-model",
        )