from fastapi import APIRouter, HTTPException

from k8s_agent.services.conversations import (
    delete_conversation,
    get_conversation,
    list_conversations,
)

router = APIRouter()


@router.get("/api/conversations")
async def list_():
    return {"conversations": list_conversations()}


@router.get("/api/conversations/{session_id}")
async def detail(session_id: str):
    r = get_conversation(session_id)
    if r is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    return r


@router.delete("/api/conversations/{session_id}")
async def delete(session_id: str):
    ok = delete_conversation(session_id)
    if not ok:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"ok": True}
