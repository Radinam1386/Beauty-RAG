
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_spring_boot_client
from app.integrations.spring_boot.client import SpringBootClient


router = APIRouter(tags=["Spring Boot"])


@router.get("/spring-boot/health")
async def spring_boot_health(
    client: Annotated[
        SpringBootClient,
        Depends(get_spring_boot_client),
    ],
):
    try:
        response = await client.request(
            "GET",
            "/actuator/health",
        )
        return response.json()

    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail="Spring Boot health check failed",
        ) from exc
