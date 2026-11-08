"""فاز ۴: محدودیت نرخ، طول پیام و سقف هزینه روزانه."""

import pytest

from app.limits import RateLimiter, rate_limiter
from tests.conftest import make_identity


def test_sliding_window_allows_under_limit():
    limiter = RateLimiter()
    now = 1000.0
    for i in range(10):
        assert limiter.hit("k", per_minute=10, per_day=30, now=now + i) == 0
    retry = limiter.hit("k", per_minute=10, per_day=30, now=now + 11)
    assert retry >= 1


def test_minute_window_frees_after_a_minute():
    limiter = RateLimiter()
    for i in range(10):
        limiter.hit("k", per_minute=10, per_day=30, now=1000 + i)
    assert limiter.hit("k", per_minute=10, per_day=30, now=1065) == 0


def test_daily_limit():
    limiter = RateLimiter()
    for i in range(30):
        limiter.hit("k", per_minute=1000, per_day=30, now=1000 + i)
    retry = limiter.hit("k", per_minute=1000, per_day=30, now=2000)
    assert retry > 60


def test_keys_are_independent():
    limiter = RateLimiter()
    for i in range(10):
        limiter.hit("a", per_minute=10, per_day=30, now=1000 + i)
    assert limiter.hit("a", per_minute=10, per_day=30, now=1011) >= 1
    assert limiter.hit("b", per_minute=10, per_day=30, now=1011) == 0


async def test_user_rate_limit_429(client):
    for _ in range(20):
        rate_limiter.hit("user:user-1", per_minute=20, per_day=200)
    resp = await client.post("/api/v1/chat", json={"content": "سلام"})
    assert resp.status_code == 429
    assert int(resp.headers["retry-after"]) >= 1
    assert "پیام" in resp.json()["detail"]


async def test_guest_rate_limit_is_per_ip(client, app):
    from app.auth.dependencies import get_identity

    app.dependency_overrides[get_identity] = lambda: make_identity(False, "guest-x")
    for _ in range(10):
        rate_limiter.hit("ip:127.0.0.1", per_minute=10, per_day=30)
    resp = await client.post("/api/v1/chat", json={"content": "سلام"})
    assert resp.status_code == 429


async def test_guest_under_limit_ok(client, app, fake_repo, fake_budget):
    from app.auth.dependencies import get_identity

    app.dependency_overrides[get_identity] = lambda: make_identity(False, "guest-y")
    resp = await client.post("/api/v1/chat", json={"content": "سلام"})
    assert resp.status_code == 200
    assert resp.json()["conversationId"]
    assert len(fake_repo.conversations) == 1
    conv = next(iter(fake_repo.conversations.values()))
    assert conv.guest_session_id == "guest-y"
    assert fake_budget.recorded == 1


async def test_long_message_422(client):
    resp = await client.post("/api/v1/chat", json={"content": "ا" * 2001})
    assert resp.status_code == 422


async def test_daily_budget_blocks_llm(client, fake_budget, fake_repo):
    fake_budget.limit = 100
    fake_budget.used = 100
    resp = await client.post("/api/v1/chat", json={"content": "سلام"})
    assert resp.status_code == 503
    assert "موقتاً" in resp.json()["detail"]
    assert fake_budget.recorded == 0
    assert fake_repo.conversations == {}


async def test_budget_records_usage(client, fake_budget):
    resp = await client.post("/api/v1/chat", json={"content": "سلام"})
    assert resp.status_code == 200
    assert fake_budget.recorded == 1
