"""فاز ۴: هویت از JWT، نشست مهمان و مالکیت گفتگو."""

import time

import jwt
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.dependencies import get_budget, get_chat_service
from app.api.v1.routes.chat import public_router, router
from app.chat.service import ChatService
from tests.conftest import JWT_SECRET, auth_headers, make_identity


@pytest.fixture
def auth_app(fake_repo, fake_llm, fake_budget) -> FastAPI:
    application = FastAPI()
    application.include_router(public_router, prefix="/api/v1")
    application.include_router(router, prefix="/api/v1")
    service = ChatService(repository=fake_repo, llm=fake_llm, tools=None)
    application.dependency_overrides[get_chat_service] = lambda: service
    application.dependency_overrides[get_budget] = lambda: fake_budget
    return application


@pytest.fixture
async def auth_client(auth_app: FastAPI):
    async with AsyncClient(
        transport=ASGITransport(app=auth_app), base_url="http://test"
    ) as ac:
        yield ac


async def test_guest_can_use_owned_conversations(auth_client, fake_repo):
    get_resp = await auth_client.get("/api/v1/conversations")
    post_resp = await auth_client.post("/api/v1/conversations", json={})
    assert get_resp.status_code == 200
    assert get_resp.json()["total"] == 0
    assert post_resp.status_code == 201
    conv = next(iter(fake_repo.conversations.values()))
    assert conv.owner_type == "guest"
    assert conv.guest_session_id


async def test_spoofed_user_header_ignored(auth_client, fake_repo):
    resp = await auth_client.post(
        "/api/v1/conversations", json={}, headers={"X-User-Id": "42"}
    )
    assert resp.status_code == 201
    assert resp.json()["ownerType"] == "guest"
    conv = next(iter(fake_repo.conversations.values()))
    assert conv.external_user_id is None
    assert conv.guest_session_id


async def test_valid_token_creates_owned_conversation(auth_client, fake_repo):
    resp = await auth_client.post(
        "/api/v1/conversations", json={"title": "من"}, headers=auth_headers("42")
    )
    assert resp.status_code == 201
    assert resp.json()["ownerType"] == "user"
    assert len(fake_repo.conversations) == 1
    conv = next(iter(fake_repo.conversations.values()))
    assert conv.external_user_id == "42"


async def test_other_user_cannot_read_conversation(auth_client, fake_repo):
    conv = await fake_repo.create_conversation(make_identity(True, "43"), title="x")
    for method, url in (
        ("get", f"/api/v1/conversations/{conv.id}/messages"),
        ("delete", f"/api/v1/conversations/{conv.id}"),
    ):
        resp = await getattr(auth_client, method)(url, headers=auth_headers("42"))
        assert resp.status_code == 404


async def test_expired_token_401(auth_client):
    exp = int(time.time()) - 60
    token = jwt.encode({"sub": "42", "exp": exp}, JWT_SECRET, algorithm="HS256")
    resp = await auth_client.get(
        "/api/v1/conversations", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 401
    assert resp.headers["www-authenticate"] == "Bearer"


async def test_bad_signature_401(auth_client):
    token = jwt.encode({"sub": "42"}, "wrong-secret", algorithm="HS256")
    resp = await auth_client.get(
        "/api/v1/conversations", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 401


async def test_malformed_authorization_header_401(auth_client):
    resp = await auth_client.get(
        "/api/v1/conversations", headers={"Authorization": "Token abc"}
    )
    assert resp.status_code == 401


async def test_guest_chat_persists(auth_client, fake_repo):
    resp = await auth_client.post("/api/v1/chat", json={"content": "سلام"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["conversationId"]
    assert body["content"] == "پاسخ آزمایشی دستیار."
    conv = next(iter(fake_repo.conversations.values()))
    assert conv.owner_type == "guest"
    assert [m.role for m in fake_repo.messages[conv.id]] == ["user", "assistant"]


async def test_authenticated_chat_persists(auth_client, fake_repo):
    resp = await auth_client.post(
        "/api/v1/chat",
        json={"content": "سلام، کمک می‌خواهم"},
        headers=auth_headers("42"),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["conversationId"]
    assert len(fake_repo.conversations) == 1
    conv = next(iter(fake_repo.conversations.values()))
    assert conv.external_user_id == "42"
    assert conv.title == "سلام، کمک می‌خواهم"
    assert [m.role for m in fake_repo.messages[conv.id]] == ["user", "assistant"]


async def test_authenticated_chat_continues_existing_conversation(auth_client, fake_repo):
    conv = await fake_repo.create_conversation(make_identity(True, "42"))
    resp = await auth_client.post(
        "/api/v1/chat",
        json={"content": "پیام دوم", "conversationId": str(conv.id)},
        headers=auth_headers("42"),
    )
    assert resp.status_code == 200
    assert resp.json()["conversationId"] == str(conv.id)
    assert len(fake_repo.conversations) == 1


async def test_chat_foreign_conversation_404(auth_client, fake_repo):
    conv = await fake_repo.create_conversation(make_identity(True, "43"))
    resp = await auth_client.post(
        "/api/v1/chat",
        json={"content": "سلام", "conversationId": str(conv.id)},
        headers=auth_headers("42"),
    )
    assert resp.status_code == 404


async def test_long_message_422(auth_client):
    resp = await auth_client.post("/api/v1/chat", json={"content": "ا" * 2001})
    assert resp.status_code == 422


async def test_blank_message_422(auth_client):
    resp = await auth_client.post("/api/v1/chat", json={"content": "   "})
    assert resp.status_code == 422
