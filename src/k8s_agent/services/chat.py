import logging
from typing import AsyncGenerator

logger = logging.getLogger(__name__)


async def stream_chat(message: str, session_id: str) -> AsyncGenerator[str, None]:
    from k8s_agent.team import team
    from k8s_agent.core.config import settings

    try:
        async for response in team.arun(
            input=message,
            session_id=session_id,
            user_id=settings.agent_user_id,
            stream=True,
        ):
            if response.content:
                yield response.content
    except Exception as e:
        logger.error("对话失败: %s", e)
        yield f"\n\n[错误: {e}]"
