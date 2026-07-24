from fastapi.testclient import TestClient

from k8s_agent.api import proxy
from k8s_agent.main import app


client = TestClient(app)


def test_web_ui_and_assets_are_served():
    page = client.get("/")
    assert page.status_code == 200
    assert "/static/app.js" in page.text
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/static/styles.css").status_code == 200


class FakeResponse:
    status_code = 200
    content = b'{"status":"ok"}'
    headers = {"content-type": "application/json"}


class FakeStreamResponse:
    status_code = 200

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return None

    async def aiter_raw(self):
        yield b'data: {"content":"connected"}\n\n'
        yield b"data: [DONE]\n\n"


class FakeClient:
    def __init__(self, *_, **__):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return None

    async def request(self, method, url, **_):
        assert method == "GET"
        assert url.endswith("/health")
        return FakeResponse()

    def stream(self, method, url, **_):
        assert method == "POST"
        assert url.endswith("/api/chat")
        return FakeStreamResponse()


def test_backend_proxy_forwards_json(monkeypatch):
    monkeypatch.setattr(proxy.httpx, "AsyncClient", FakeClient)
    response = client.get("/backend/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_backend_proxy_preserves_chat_stream(monkeypatch):
    monkeypatch.setattr(proxy.httpx, "AsyncClient", FakeClient)
    response = client.post(
        "/backend/api/chat",
        json={"message": "hello", "session_id": "session-1"},
    )
    assert response.status_code == 200
    assert "connected" in response.text
    assert "[DONE]" in response.text
