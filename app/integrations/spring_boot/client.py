
from typing import Any

import httpx


class SpringBootClient:
    def __init__(
        self,
        base_url: str,
        timeout: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/") + "/",
            timeout=timeout,
            transport=transport,
        )

    async def request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> httpx.Response:
        response = await self._client.request(
            method,
            path.lstrip("/"),
            **kwargs,
        )
        response.raise_for_status()
        return response

    async def aclose(self) -> None:
        await self._client.aclose()
