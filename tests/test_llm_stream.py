import httpx
import respx

from app.ai.llm import OpenAICompatibleClient


BASE = "https://llm.test/v1"


@respx.mock
async def test_stream_chat_parses_sse():
    async def sse(request):
        body = (
            b'data: {"choices":[{"delta":{"content":"Sa"}}]}\n\n'
            b'data: {"choices":[{"delta":{"content":"lam"}}]}\n\n'
            b"data: [DONE]\n\n"
        )
        return httpx.Response(200, content=body, headers={"content-type": "text/event-stream"})

    respx.post(f"{BASE}/chat/completions").mock(side_effect=sse)
    client = OpenAICompatibleClient(base_url=BASE, api_key="k", model="m", max_retries=0)
    chunks = [c async for c in client.stream_chat([{"role": "user", "content": "hi"}])]
    assert "".join(chunks) == "Salam"
    await client.aclose()
