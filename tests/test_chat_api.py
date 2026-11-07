import json

import pytest

from app.ai.llm import FakeLLMClient
from tests.conftest import FakeChatRepository, make_identity


async def test_real_dependency_wiring(fake_repo, fake_llm):
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient
    from app.api.dependencies import get_chat_repository, get_llm_client
    from app.api.v1.routes.chat import router
    from app.integrations.spring_boot.client import SpringBootClient

    application = FastAPI()
    application.include_router(router, prefix="/api/v1")
    # مثل lifespan برنامه: کلاینت سایت در state قرار می‌گیرد
    application.state.spring_boot_client = SpringBootClient(base_url="http://spring.test")
    application.dependency_overrides[get_chat_repository] = lambda: fake_repo
    application.dependency_overrides[get_llm_client] = lambda: fake_llm
    async with AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as client:
        response = await client.post('/api/v1/conversations', json={}, headers={'X-Guest-Session-Id': 'test-guest'})
        assert response.status_code == 201
        response = await client.post(
            f"/api/v1/conversations/{response.json()['id']}/messages",
            json={'content': 'سلام'}, headers={'X-Guest-Session-Id': 'test-guest'},
        )
        assert response.status_code == 200

    await application.state.spring_boot_client.aclose()


async def test_create_conversation_201(client):
    resp = await client.post("/api/v1/conversations", json={"title": "گفتگوی من"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "گفتگوی من"
    assert body["ownerType"] == "guest"  # camelCase
    assert "createdAt" in body
    assert "id" in body


async def test_list_conversations_paginated(client, fake_repo, guest):
    for i in range(5):
        await fake_repo.create_conversation(guest, title=f"c{i}")
    resp = await client.get("/api/v1/conversations", params={"page": 1, "pageSize": 2})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 5
    assert len(body["items"]) == 2
    assert body["page"] == 1
    assert body["pageSize"] == 2
    assert body["pages"] == 3


async def test_send_message_roundtrip(client, fake_repo, guest):
    created = (await client.post("/api/v1/conversations", json={"title": None})).json()
    cid = created["id"]
    resp = await client.post(
        f"/api/v1/conversations/{cid}/messages",
        json={"content": "سلام دستیار"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["conversationId"] == cid
    assert body["userMessage"]["content"] == "سلام دستیار"
    assert body["assistantMessage"]["role"] == "assistant"
    assert body["assistantMessage"]["content"] == "پاسخ آزمایشی دستیار."


async def test_send_message_empty_422(client, fake_repo, guest):
    created = (await client.post("/api/v1/conversations", json={})).json()
    resp = await client.post(
        f"/api/v1/conversations/{created['id']}/messages",
        json={"content": "  "},
    )
    assert resp.status_code == 422


async def test_messages_of_other_owner_404(client, fake_repo, guest, user):
    conv = await fake_repo.create_conversation(user, title="کاربر")
    resp = await client.get(f"/api/v1/conversations/{conv.id}/messages")
    assert resp.status_code == 404


async def test_delete_conversation_204(client, fake_repo, guest):
    conv = await fake_repo.create_conversation(guest, title="حذف")
    resp = await client.delete(f"/api/v1/conversations/{conv.id}")
    assert resp.status_code == 204
    resp2 = await client.get(f"/api/v1/conversations/{conv.id}/messages")
    assert resp2.status_code == 404


async def test_stream_sse(client):
    created = (await client.post("/api/v1/conversations", json={"title": "استریم"})).json()
    resp = await client.post(
        f"/api/v1/conversations/{created['id']}/messages/stream",
        json={"content": "سلام"},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    text = resp.text
    assert "event: delta" in text
    assert "event: done" in text
    # پیام کاربر ذخیره شده
    msgs = await client.get(f"/api/v1/conversations/{created['id']}/messages")
    roles = [m["role"] for m in msgs.json()]
    assert "user" in roles
    assert "assistant" in roles


async def test_identity_header_user(client, app, fake_repo, fake_llm):
    from app.auth.dependencies import get_identity
    from tests.conftest import make_identity

    app.dependency_overrides[get_identity] = lambda: make_identity(True, "77")
    created = (await client.post("/api/v1/conversations", json={"title": "من"})).json()
    assert created["ownerType"] == "user"
    items = (await client.get("/api/v1/conversations")).json()
    assert items["total"] == 1
