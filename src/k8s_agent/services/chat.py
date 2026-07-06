import logging
from typing import AsyncGenerator

logger = logging.getLogger(__name__)


async def stream_chat(message: str) -> AsyncGenerator[str, None]:
    from k8s_agent.agent import agent

    try:
        async for response in agent.arun(input=message, stream=True):
            if response.content:
                yield response.content
    except Exception as e:
        logger.error("对话失败: %s", e)
        yield f"\n\n[错误: {e}]"
