import json
import asyncio
import logging
import time
from typing import Any, AsyncIterator

import httpx

from app.ai.llm.base import LLMClient, LLMResponse, Message, Usage
from app.ai.llm.errors import (
    LLMAuthError,
    LLMBadResponseError,
    LLMRateLimitError,
    LLMServerError,
    LLMTimeoutError,
)
from app.core.config import get_settings

logger = logging.getLogger(__name__)

RETRY_ERRORS = (LLMTimeoutError, LLMRateLimitError, LLMServerError)


class OpenAICompatibleClient(LLMClient):
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        connect_timeout: float = 5,
        read_timeout: float = 60,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        self.model = model
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.http = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=httpx.Timeout(read_timeout, connect=connect_timeout),
        )

    async def chat(self, messages: list[Message], **opts: Any) -> LLMResponse:
        payload = {"model": self.model, "messages": messages, **opts}
        if payload.get("tools") is None:
            payload.pop("tools", None)
        start = time.perf_counter()

        for attempt in range(self.max_retries + 1):
            try:
                data = await self._send(payload)
                break
            except RETRY_ERRORS as error:
                if attempt == self.max_retries:
                    raise
                wait = self.retry_delay * 2**attempt
                logger.warning("LLM error: %s. retrying in %.0fs", type(error).__name__, wait)
                await asyncio.sleep(wait)

        latency_ms = int((time.perf_counter() - start) * 1000)
        return self._parse(data, latency_ms)

    def _parse(self, data: dict, latency_ms: int) -> LLMResponse:
        try:
            choice = data["choices"][0]
            usage = data.get("usage") or {}
            message = choice.get("message") or {}
            tool_calls = message.get("tool_calls") or []
            return LLMResponse(
                content=message.get("content"),
                usage=Usage(
                    prompt_tokens=usage.get("prompt_tokens", 0),
                    completion_tokens=usage.get("completion_tokens", 0),
                ),
                finish_reason=choice.get("finish_reason"),
                model=data.get("model", self.model),
                latency_ms=latency_ms,
                tool_calls=list(tool_calls),
            )
        except (KeyError, IndexError, TypeError) as error:
            raise LLMBadResponseError("unexpected response format") from error

    async def stream_chat(self, messages: list[Message], **opts: Any) -> AsyncIterator[str]:
        """SSE استریم OpenAI-compatible از مسیر /chat/completions."""
        payload = {"model": self.model, "messages": messages, "stream": True, **opts}
        if payload.get("tools") is None:
            payload.pop("tools", None)

        try:
            async with self.http.stream("POST", "/chat/completions", json=payload) as response:
                if response.status_code in (401, 403):
                    raise LLMAuthError(f"bad API key ({response.status_code})")
                if response.status_code == 429:
                    raise LLMRateLimitError("too many requests")
                if response.status_code >= 500:
                    raise LLMServerError(f"server error ({response.status_code})")
                if response.status_code >= 400:
                    raise LLMBadResponseError(f"request rejected ({response.status_code})")

                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    if not data:
                        continue
                    try:
                        chunk = json.loads(data)
                    except ValueError:
                        continue
                    choices = chunk.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta") or {}
                    content = delta.get("content")
                    if content:
                        yield content
        except httpx.TimeoutException as error:
            raise LLMTimeoutError("model took too long") from error
        except httpx.HTTPError as error:
            raise LLMServerError("connection problem") from error

    async def _send(self, payload: dict) -> dict:
        """یک درخواست می‌فرستد و مشکل‌ها را به خطاهای خودمان تبدیل می‌کند."""
        try:
            response = await self.http.post("/chat/completions", json=payload)
        except httpx.TimeoutException as error:
            raise LLMTimeoutError("model took too long") from error
        except httpx.HTTPError as error:
            raise LLMServerError("connection problem") from error

        code = response.status_code
        if code in (401, 403):
            raise LLMAuthError(f"bad API key ({code})")
        if code == 429:
            raise LLMRateLimitError("too many requests")
        if code >= 500:
            raise LLMServerError(f"server error ({code})")
        if code >= 400:
            raise LLMBadResponseError(f"request rejected ({code})")

        try:
            return response.json()
        except ValueError as error:
            raise LLMBadResponseError("response is not JSON") from error

    async def aclose(self) -> None:
        await self.http.aclose()


def create_llm_client() -> OpenAICompatibleClient:
    """کلاینت را با مقدارهای فایل .env می‌سازد."""
    settings = get_settings()
    key_provider = settings.llm_api_key
    raw_key = key_provider.get_secret_value()
    return OpenAICompatibleClient(
        base_url=settings.llm_base_url,
        api_key=raw_key,
        model=settings.llm_model,
        connect_timeout=settings.llm_connect_timeout,
        read_timeout=settings.llm_read_timeout,
        max_retries=settings.llm_max_retries,
    )
