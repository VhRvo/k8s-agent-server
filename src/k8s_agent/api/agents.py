import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from k8s_agent.services.agents import stream_agent_chat
from k8s_agent.team import direct_agents, get_agent_profiles

router = APIRouter()


class AgentChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: str = Field(min_length=1, max_length=200)
    context: list[str] = Field(default_factory=list, max_length=10)


@router.get("/api/agents")
async def list_agents():
    return {"agents": get_agent_profiles()}


@router.post("/api/agents/{agent_id}/chat")
async def chat_with_agent(agent_id: str, req: AgentChatRequest):
    if agent_id not in direct_agents:
        raise HTTPException(status_code=404, detail="Agent 不存在")

    async def event_stream():
        async for content in stream_agent_chat(
            agent_id,
            req.message,
            req.session_id,
            req.context,
        ):
            payload = {"agent": agent_id, "content": content}
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
