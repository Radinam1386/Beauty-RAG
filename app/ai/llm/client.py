import asyncio
import logging
import time
from typing import Any

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
        start = time.perf_counter()

        # تلاش اول + چند بار تلاش مجدد
        for attempt in range(self.max_retries + 1):
            try:
                data = await self._send(payload)
                break
            except RETRY_ERRORS as error:
                if attempt == self.max_retries:
                    raise  # تلاش‌ها تمام شد
                wait = self.retry_delay * 2**attempt  # 1، 2، 4 ثانیه
                logger.warning("LLM error: %s. retrying in %.0fs", type(error).__name__, wait)
                await asyncio.sleep(wait)

        latency_ms = int((time.perf_counter() - start) * 1000)

        try:
            choice = data["choices"][0]
            usage = data.get("usage") or {}
            response = LLMResponse(
                content=choice["message"]["content"],
                usage=Usage(
                    prompt_tokens=usage.get("prompt_tokens", 0),
                    completion_tokens=usage.get("completion_tokens", 0),
                ),
                finish_reason=choice.get("finish_reason"),
                model=data.get("model", self.model),
                latency_ms=latency_ms,
            )
        except (KeyError, IndexError, TypeError) as error:
            raise LLMBadResponseError("unexpected response format") from error

        # فقط آمار لاگ می‌شود، نه متن پیام‌ها
        logger.info(
            "LLM ok: model=%s prompt_tokens=%d completion_tokens=%d latency_ms=%d",
            response.model,
            response.usage.prompt_tokens,
            response.usage.completion_tokens,
            latency_ms,
        )
        return response

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
    s = get_settings()
    return OpenAICompatibleClient(
        base_url=s.llm_base_url,
        api_key=s.llm_api_key.get_secret_value(),
        model=s.llm_model,
        connect_timeout=s.llm_connect_timeout,
        read_timeout=s.llm_read_timeout,
        max_retries=s.llm_max_retries,
    )