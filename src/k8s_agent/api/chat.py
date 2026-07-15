import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from k8s_agent.services.chat import stream_chat
from k8s_agent.services.conversations import set_title_if_new

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    session_id: str


@router.post("/api/chat")
async def chat(req: ChatRequest):
    async def event_stream():
        async for content in stream_chat(req.message, req.session_id):
            yield f"data: {json.dumps({'content': content}, ensure_ascii=False)}\n\n"
        set_title_if_new(req.session_id, req.message)
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
