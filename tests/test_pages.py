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


class MissingStreamResponse(FakeStreamResponse):
    status_code = 404


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


class AgentFallbackClient(FakeClient):
    calls = []

    def stream(self, method, url, **_):
        self.calls.append(url)
        if "/api/agents/" in url:
            return MissingStreamResponse()
        return FakeStreamResponse()


def test_agent_proxy_falls_back_for_older_backend(monkeypatch):
    AgentFallbackClient.calls = []
    monkeypatch.setattr(proxy.httpx, "AsyncClient", AgentFallbackClient)
    response = client.post(
        "/backend/api/agents/analyst/chat",
        json={
            "message": "analyze",
            "session_id": "case-1-analyst",
            "context": ["pod restarted"],
        },
    )
    assert response.status_code == 200
    assert "connected" in response.text
    assert len(AgentFallbackClient.calls) == 2
    assert AgentFallbackClient.calls[0].endswith("/api/agents/analyst/chat")
    assert AgentFallbackClient.calls[1].endswith("/api/chat")


def test_operator_proxy_uses_safe_local_plan_for_older_backend(monkeypatch):
    AgentFallbackClient.calls = []
    monkeypatch.setattr(proxy.httpx, "AsyncClient", AgentFallbackClient)
    response = client.post(
        "/backend/api/agents/operator/chat",
        json={
            "message": "restart deployment",
            "session_id": "case-1-operator",
            "context": ["deployment api has unavailable replicas"],
        },
    )
    assert response.status_code == 200
    assert "安全兼容方案草案" in response.text
    assert "restart deployment" in response.text
    assert "deployment api has unavailable replicas" in response.text
    assert "[DONE]" in response.text
    assert len(AgentFallbackClient.calls) == 1
    assert AgentFallbackClient.calls[0].endswith("/api/agents/operator/chat")
