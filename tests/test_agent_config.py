from k8s_agent.agent import agent


def test_agent_has_session_db():
    assert agent.db is not None


def test_agent_history_enabled():
    assert agent.add_history_to_context is True
    assert agent.store_history_messages is True
    assert agent.num_history_messages == 20
