from fastapi.testclient import TestClient
from app import app

client = TestClient(app, raise_server_exceptions=False)


def test_chat_requires_auth():
    r = client.post("/chat", json={"user_id": "u1", "session_id": "s1", "message": "hi"})
    assert r.status_code == 401


def test_settings_requires_auth():
    r = client.get("/settings")
    assert r.status_code == 403  # require_admin always returns 403


def test_upload_requires_auth():
    r = client.post("/upload", files={"file": ("t.pdf", b"data", "application/pdf")})
    assert r.status_code == 403  # require_admin always returns 403


def test_user_key_denied_admin_route():
    r = client.get("/settings", headers={"X-API-Key": "test-user-key"})
    assert r.status_code == 403


def test_admin_key_reads_settings():
    r = client.get("/settings", headers={"X-API-Key": "test-admin-key"})
    assert r.status_code == 200
