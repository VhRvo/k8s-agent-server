from fastapi.testclient import TestClient

from k8s_agent.main import app


def test_list_conversations_route():
    with TestClient(app) as client:
        resp = client.get("/api/conversations")
    assert resp.status_code == 200
    assert "conversations" in resp.json()


def test_get_conversation_not_found(monkeypatch):
    from k8s_agent.api import conversations as api_conv
    monkeypatch.setattr(api_conv, "get_conversation", lambda sid: None)
    with TestClient(app) as client:
        resp = client.get("/api/conversations/nope")
    assert resp.status_code == 404


def test_delete_conversation_not_found(monkeypatch):
    from k8s_agent.api import conversations as api_conv
    monkeypatch.setattr(api_conv, "delete_conversation", lambda sid: False)
    with TestClient(app) as client:
        resp = client.delete("/api/conversations/nope")
    assert resp.status_code == 404
