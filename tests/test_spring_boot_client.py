
import asyncio

import httpx

from app.integrations.spring_boot.client import SpringBootClient


class MockAsyncTransport(httpx.AsyncBaseTransport):
    async def handle_async_request(
        self,
        request: httpx.Request,
    ) -> httpx.Response:
        assert str(request.url) == (
            "http://spring-boot:8080/api/health"
        )

        return httpx.Response(
            200,
            json={"status": "UP"},
        )

    async def aclose(self) -> None:
        pass


def test_spring_boot_client() -> None:
    async def run_test() -> None:
        client = SpringBootClient(
            base_url="http://spring-boot:8080",
            transport=MockAsyncTransport(),
        )

        try:
            response = await client.request(
                "GET",
                "/api/health",
            )

            assert response.status_code == 200
            assert response.json() == {"status": "UP"}

        finally:
            await client.aclose()

    asyncio.run(run_test())
