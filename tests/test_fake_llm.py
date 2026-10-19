import pytest

from app.ai.llm import FakeLLMClient, LLMTimeoutError


async def test_fake_reply():
    response = await FakeLLMClient().chat([{"role": "user", "content": "سلام"}])
    assert response.content
    assert response.usage.prompt_tokens > 0


async def test_fake_error():
    with pytest.raises(LLMTimeoutError):
        await FakeLLMClient(error=LLMTimeoutError()).chat([])