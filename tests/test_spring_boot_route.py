
import asyncio
import httpx

from fastapi import FastAPI

from app.api.dependencies import get_spring_boot_client
from app.api.v1.routes.spring_boot import router as spring_boot_router
from app.integrations.spring_boot.client import SpringBootClient


class FakeJavaTransport(httpx.AsyncBaseTransport):

    async def handle_async_request(
        self,
        request: httpx.Request,
    ) -> httpx.Response:

        assert request.method == "GET"
        assert request.url.path == "/actuator/health"

        return httpx.Response(
            200,
            json={"status": "UP"},
        )


def test_spring_boot_health_route():

    async def run_test():

        spring_client = SpringBootClient(
            base_url="http://spring-boot:8080",
            transport=FakeJavaTransport(),
        )

        test_app = FastAPI()
        test_app.include_router(
            spring_boot_router,
            prefix="/api/v1",
        )

        test_app.dependency_overrides[
            get_spring_boot_client
        ] = lambda: spring_client

        try:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=test_app),
                base_url="http://testserver",
            ) as client:

                response = await client.get(
                    "/api/v1/spring-boot/health"
                )

            assert response.status_code == 200
            assert response.json() == {"status": "UP"}

        finally:
            await spring_client.aclose()

    asyncio.run(run_test())



class FakeErrorJavaTransport(httpx.AsyncBaseTransport):

    async def handle_async_request(
        self,
        request: httpx.Request,
    ) -> httpx.Response:

        assert request.method == "GET"
        assert request.url.path == "/actuator/health"

        return httpx.Response(
            503,
            json={"detail": "Service Unavailable"},
        )

    
def test_spring_boot_health_when_java_fails():

    async def run_test():

        spring_client = SpringBootClient(
            base_url="http://spring-boot:8080",
            transport=FakeErrorJavaTransport(),
        )

        test_app = FastAPI()

        test_app.include_router(
            spring_boot_router,
            prefix="/api/v1",
        )

        test_app.dependency_overrides[
            get_spring_boot_client
        ] = lambda: spring_client

        try:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=test_app),
                base_url="http://testserver",
            ) as client:

                response = await client.get(
                    "/api/v1/spring-boot/health"
                )

            assert response.status_code == 502
            assert response.json() == {
                "detail": "Spring Boot health check failed"
            }

        finally:
            await spring_client.aclose()

    asyncio.run(run_test())

