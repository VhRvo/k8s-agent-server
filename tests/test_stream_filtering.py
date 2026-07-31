import asyncio

from agno.run.agent import (
    IntermediateRunContentEvent as AgentIntermediateRunContentEvent,
)
from agno.run.agent import RunContentEvent as AgentRunContentEvent
from agno.run.team import (
    IntermediateRunContentEvent as TeamIntermediateRunContentEvent,
)
from agno.run.team import RunContentEvent as TeamRunContentEvent

from k8s_agent import team as team_module
from k8s_agent.services import agents as agents_service
from k8s_agent.services import chat as chat_service


async def _collect(stream):
    return [item async for item in stream]


def test_team_stream_omits_intermediate_content(monkeypatch):
    class FakeTeam:
        async def arun(self, **_):
            yield TeamIntermediateRunContentEvent(content="协调和工具过程")
            yield TeamRunContentEvent(content="最终答复")

    monkeypatch.setattr(team_module, "team", FakeTeam())

    result = asyncio.run(_collect(chat_service.stream_chat("hi", "session-1")))

    assert result == ["最终答复"]


def test_direct_agent_stream_omits_intermediate_content(monkeypatch):
    class FakeAgent:
        async def arun(self, **_):
            yield AgentIntermediateRunContentEvent(content="工具过程")
            yield AgentRunContentEvent(content="最终答复")

    monkeypatch.setitem(agents_service.direct_agents, "analyst", FakeAgent())

    result = asyncio.run(
        _collect(
            agents_service.stream_agent_chat(
                "analyst",
                "hi",
                "session-1",
                [],
            )
        )
    )

    assert result == ["最终答复"]
