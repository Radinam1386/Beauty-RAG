from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "beauty-rag"
    assert body["status"] in ("ok", "degraded")
    assert "database" in body


def test_root():
    response = client.get("/")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "BeautyBoss AI"
    assert body["chat"] == "/api/v1/conversations"
