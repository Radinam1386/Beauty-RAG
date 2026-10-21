
from fastapi import Request

from app.integrations.spring_boot.client import SpringBootClient


def get_spring_boot_client(request: Request) -> SpringBootClient:
    return request.app.state.spring_boot_client
