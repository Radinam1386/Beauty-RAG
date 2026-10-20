import httpx
import pytest
import respx

from app.ai.llm import (
    LLMAuthError,
    LLMServerError,
    LLMTimeoutError,
    OpenAICompatibleClient,
)

BASE = "https://llm.test/v1"
URL = f"{BASE}/chat/completions"
MESSAGES = [{"role": "user", "content": "سلام"}]

OK_BODY = {
    "model": "test-model",
    "choices": [{"message": {"content": "سلام!"}, "finish_reason": "stop"}],
    "usage": {"prompt_tokens": 7, "completion_tokens": 3},
}


def make_client() -> OpenAICompatibleClient:
    return OpenAICompatibleClient(
        base_url=BASE, api_key="test", model="test-model", max_retries=2, retry_delay=0
    )


@respx.mock
async def test_success():
    respx.post(URL).mock(return_value=httpx.Response(200, json=OK_BODY))
    response = await make_client().chat(MESSAGES)
    assert response.content == "سلام!"
    assert response.usage.prompt_tokens == 7


@respx.mock
async def test_retry_then_success():
    route = respx.post(URL).mock(
        side_effect=[httpx.Response(429), httpx.Response(200, json=OK_BODY)]
    )
    response = await make_client().chat(MESSAGES)
    assert response.content == "سلام!"
    assert route.call_count == 2  # یک بار شکست، یک بار موفق


@respx.mock
async def test_gives_up_after_retries():
    route = respx.post(URL).mock(return_value=httpx.Response(500))
    with pytest.raises(LLMServerError):
        await make_client().chat(MESSAGES)
    assert route.call_count == 3  # یک بار اول + دو بار تلاش مجدد


@respx.mock
async def test_timeout():
    respx.post(URL).mock(side_effect=httpx.ReadTimeout("slow"))
    with pytest.raises(LLMTimeoutError):
        await make_client().chat(MESSAGES)


@respx.mock
async def test_no_retry_on_bad_key():
    route = respx.post(URL).mock(return_value=httpx.Response(401))
    with pytest.raises(LLMAuthError):
        await make_client().chat(MESSAGES)
    assert route.call_count == 1  # دوباره تلاش نکرد