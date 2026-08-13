"""FastAPI endpoint tests."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["llm_mode"] == "mock"


def test_chat_session_flow():
    session_id = "api-session-1"
    r1 = client.post("/chat", json={"session_id": session_id, "message": "Hi there"})
    assert r1.status_code == 200
    assert r1.json()["fully_verified"] is False

    r2 = client.post(
        "/chat",
        json={
            "session_id": session_id,
            "message": "My name is Lisa phone +1122334455 IBAN DE89370400440532013000",
        },
    )
    assert r2.status_code == 200
    assert r2.json()["phase"] == "awaiting_secret"

    r3 = client.post("/chat", json={"session_id": session_id, "message": "Yoda"})
    assert r3.status_code == 200
    body = r3.json()
    assert body["fully_verified"] is True
    assert body["client_type"] == "premium"
    assert "+1999888999" in body["reply"]
    assert body["turn"] == 3
    assert len(body["history"]) >= 4
    remembered = client.get(f"/sessions/{session_id}")
    assert remembered.status_code == 200
    assert remembered.json()["fully_verified"] is True
    assert remembered.json()["turn"] == 3


def test_reset_session():
    session_id = "api-session-reset"
    client.post("/chat", json={"session_id": session_id, "message": "Hello"})
    deleted = client.delete(f"/sessions/{session_id}")
    assert deleted.status_code == 200
    missing = client.get(f"/sessions/{session_id}")
    assert missing.status_code == 404
    again = client.post("/chat", json={"session_id": session_id, "message": "Hello"})
    assert again.json()["phase"] == "collecting_identity"
