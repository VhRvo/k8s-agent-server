import pytest

from k8s_agent.api.chat import ChatRequest


def test_chat_request_requires_session_id():
    with pytest.raises(Exception):
        ChatRequest(message="hi")


def test_chat_request_with_session_id():
    req = ChatRequest(message="hi", session_id="abc")
    assert req.message == "hi"
    assert req.session_id == "abc"
