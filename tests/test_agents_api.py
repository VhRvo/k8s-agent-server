from fastapi.testclient import TestClient

from k8s_agent.api import agents as agents_api
from k8s_agent.main import app
from k8s_agent.services.agents import build_agent_input
from k8s_agent.team import direct_agents


client = TestClient(app)


def test_list_agents_includes_team_and_specialists():
    response = client.get("/api/agents")
    assert response.status_code == 200
    profiles = response.json()["agents"]
    assert [item["id"] for item in profiles] == [
        "team",
        "investigator",
        "analyst",
        "operator",
    ]
    operator = next(item for item in profiles if item["id"] == "operator")
    assert operator["available"] is False
    assert "后续版本" in operator["availability_note"]


def test_agent_chat_streams_selected_agent(monkeypatch):
    async def fake_stream(agent_id, message, session_id, context):
        assert (agent_id, message, session_id) == (
            "analyst",
            "find root cause",
            "case-1-analyst",
        )
        assert context == ["pod restarted"]
        yield "root cause"

    monkeypatch.setattr(agents_api, "stream_agent_chat", fake_stream)
    response = client.post(
        "/api/agents/analyst/chat",
        json={
            "message": "find root cause",
            "session_id": "case-1-analyst",
            "context": ["pod restarted"],
        },
    )
    assert response.status_code == 200
    assert '"agent": "analyst"' in response.text
    assert "root cause" in response.text
    assert "[DONE]" in response.text


def test_unknown_agent_is_rejected():
    response = client.post(
        "/api/agents/unknown/chat",
        json={"message": "hello", "session_id": "case-1"},
    )
    assert response.status_code == 404


def test_direct_agents_enforce_safe_tool_boundaries():
    investigator_tools = {tool.name for tool in direct_agents["investigator"].tools}
    assert "kubectl_exec" not in investigator_tools
    assert direct_agents["operator"].tools == []


def test_agent_input_includes_shared_context():
    result = build_agent_input("analyze", [" pod restarted ", "node pressure"])
    assert "[共享证据 1]\npod restarted" in result
    assert "[共享证据 2]\nnode pressure" in result
    assert result.endswith("[用户问题]\nanalyze")
