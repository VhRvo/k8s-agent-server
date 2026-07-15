from agno.models.message import Message
from agno.run.agent import RunOutput
from agno.run.base import RunStatus
from agno.session.agent import AgentSession

from k8s_agent.services import conversations


def test_derive_title_truncates():
    assert conversations.derive_title("a" * 50) == "a" * 30


def test_derive_title_strips_and_collapses_newlines():
    assert conversations.derive_title("  hello\nworld  ") == "hello world"


def test_derive_title_empty():
    assert conversations.derive_title("") == "新对话"
    assert conversations.derive_title("   ") == "新对话"
    assert conversations.derive_title(None) == "新对话"


def test_serialize_session_summary():
    s = AgentSession(
        session_id="s1",
        session_data={"session_name": "标题"},
        created_at=1730000000,
        updated_at=1730000100,
    )
    out = conversations.serialize_session_summary(s)
    assert out["id"] == "s1"
    assert out["title"] == "标题"
    assert out["created_at"]
    assert out["updated_at"]


def test_serialize_session_summary_default_title():
    s = AgentSession(session_id="s2", session_data=None)
    out = conversations.serialize_session_summary(s)
    assert out["title"] == "新对话"


def _make_session(messages, title="T", sid="s1"):
    run = RunOutput(
        run_id="r1",
        agent_id="a",
        messages=[Message(role=r, content=c) for r, c in messages],
        status=RunStatus.completed,
    )
    data = {"session_name": title} if title else None
    return AgentSession(session_id=sid, session_data=data, runs=[run])


def test_serialize_session_messages():
    s = _make_session([("user", "hi"), ("assistant", "hello")])
    out = conversations.serialize_session_messages(s)
    assert out["id"] == "s1"
    assert out["title"] == "T"
    assert [m["role"] for m in out["messages"]] == ["user", "assistant"]
    assert out["messages"][0]["content"] == "hi"


def test_list_conversations_maps_and_sorts(monkeypatch):
    fake = [
        AgentSession(session_id="a", session_data={"session_name": "A"}, created_at=100, updated_at=100),
        AgentSession(session_id="b", session_data={"session_name": "B"}, created_at=200, updated_at=200),
    ]
    monkeypatch.setattr(conversations.agent.db, "get_sessions", lambda **kw: fake)
    result = conversations.list_conversations()
    assert [c["id"] for c in result] == ["b", "a"]


def test_list_conversations_handles_tuple_return(monkeypatch):
    fake = [AgentSession(session_id="a", session_data={"session_name": "A"}, created_at=100, updated_at=100)]
    monkeypatch.setattr(conversations.agent.db, "get_sessions", lambda **kw: (fake, 1))
    result = conversations.list_conversations()
    assert [c["id"] for c in result] == ["a"]


def test_get_conversation_returns_none_when_missing(monkeypatch):
    monkeypatch.setattr(conversations.agent, "get_session", lambda **kw: None)
    assert conversations.get_conversation("nope") is None


def test_get_conversation_serializes(monkeypatch):
    s = _make_session([("user", "hi"), ("assistant", "hello")])
    monkeypatch.setattr(conversations.agent, "get_session", lambda **kw: s)
    result = conversations.get_conversation("s1")
    assert result["id"] == "s1"
    assert [m["role"] for m in result["messages"]] == ["user", "assistant"]


def test_delete_conversation(monkeypatch):
    deleted = []
    monkeypatch.setattr(conversations.agent.db, "delete_session", lambda sid, **kw: deleted.append(sid))
    assert conversations.delete_conversation("s1") is True
    assert deleted == ["s1"]


def test_delete_conversation_failure(monkeypatch):
    def boom(sid, **kw):
        raise RuntimeError("x")
    monkeypatch.setattr(conversations.agent.db, "delete_session", boom)
    assert conversations.delete_conversation("s1") is False


def test_set_title_if_new_renames(monkeypatch):
    session = AgentSession(session_id="s1", session_data={})
    monkeypatch.setattr(conversations.agent, "get_session", lambda **kw: session)
    calls = {}

    def fake_rename(**kw):
        calls.update(kw)

    monkeypatch.setattr(conversations.agent.db, "rename_session", fake_rename)
    conversations.set_title_if_new("s1", "检查集群健康状况")
    assert calls["session_name"] == "检查集群健康状况"
    assert calls["session_type"].value == "agent"


def test_set_title_if_new_skips_when_titled(monkeypatch):
    session = AgentSession(session_id="s1", session_data={"session_name": "已有标题"})
    monkeypatch.setattr(conversations.agent, "get_session", lambda **kw: session)
    called = []
    monkeypatch.setattr(conversations.agent.db, "rename_session", lambda **kw: called.append(kw))
    conversations.set_title_if_new("s1", "新消息")
    assert called == []
