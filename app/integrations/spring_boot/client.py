"""کلاینت بک‌اند سایت (Spring Boot) — API واقعی beautyboss.ir.

مسیرهای عمومی که سایت خودش استفاده می‌کند:
- POST /api/v1/elastic/search-by-filter?page=&size=  با بدنه {"keyword", "adType"}
- GET  /api/v1/spacerentalad/get-one?id=
- GET  /api/v1/equipmentad/get-one?id=
"""

from typing import Any

import httpx

API_PREFIX = "/api/v1"

# فقط مسیرهایی که روی سایت واقعی تست شده‌اند
DETAIL_PATHS = {
    "SPACE_RENTAL": "spacerentalad/get-one",
    "EQUIPMENT": "equipmentad/get-one",
}


class SpringBootError(RuntimeError):
    """ارتباط با سایت یا پاسخ نامعتبر."""


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

    async def _json(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            response = await self.request(method, path, **kwargs)
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise SpringBootError(str(exc)) from exc

    async def search_ads(
        self,
        keyword: str = "",
        ad_type: str | None = None,
        page: int = 0,
        size: int = 24,
    ) -> dict:
        body: dict[str, Any] = {}
        if keyword.strip():
            body["keyword"] = keyword.strip()
        if ad_type:
            body["adType"] = ad_type
        data = await self._json(
            "POST",
            f"{API_PREFIX}/elastic/search-by-filter",
            params={"page": page, "size": size},
            json=body,
        )
        if not isinstance(data, dict) or not isinstance(data.get("content"), list):
            raise SpringBootError("پاسخ جستجوی آگهی نامعتبر است")
        return data

    async def get_ad(self, ad_id: str, ad_type: str) -> dict | None:
        path = DETAIL_PATHS.get(ad_type)
        if not path:
            return None
        try:
            data = await self._json(
                "GET", f"{API_PREFIX}/{path}", params={"id": ad_id}
            )
        except SpringBootError:
            return None
        return data if isinstance(data, dict) else None

    async def aclose(self) -> None:
        await self._client.aclose()
