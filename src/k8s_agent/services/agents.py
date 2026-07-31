import logging
from typing import AsyncGenerator

from k8s_agent.core.config import settings
from k8s_agent.team import direct_agents

logger = logging.getLogger(__name__)


def build_agent_input(message: str, context: list[str]) -> str:
    items = [item.strip()[:4000] for item in context[:10] if item.strip()]
    if not items:
        return message
    evidence = "\n\n".join(f"[共享证据 {index + 1}]\n{item}" for index, item in enumerate(items))
    return f"{evidence}\n\n[用户问题]\n{message}"


async def stream_agent_chat(
    agent_id: str,
    message: str,
    session_id: str,
    context: list[str],
) -> AsyncGenerator[str, None]:
    from agno.run.agent import RunContentEvent

    agent = direct_agents[agent_id]
    try:
        async for response in agent.arun(
            input=build_agent_input(message, context),
            session_id=session_id,
            user_id=f"{settings.agent_user_id}:{agent_id}",
            stream=True,
        ):
            if isinstance(response, RunContentEvent) and response.content:
                yield str(response.content)
    except Exception as exc:
        logger.error("Agent 对话失败 agent_id=%s: %s", agent_id, exc)
        yield f"\n\n[错误: {exc}]"
