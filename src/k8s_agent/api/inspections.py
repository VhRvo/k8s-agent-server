from fastapi import APIRouter

from k8s_agent.models.inspection import store
from k8s_agent.services.inspector import start_inspection

router = APIRouter()


@router.get("/api/inspections")
async def list_inspections():
    return {"records": store.list()}


@router.get("/api/inspections/{record_id}")
async def get_inspection(record_id: str):
    r = store.get(record_id)
    if r is None:
        return {"error": "记录不存在"}
    return r


@router.post("/api/inspect")
async def inspect():
    record_id = start_inspection(trigger="manual")
    return {"id": record_id, "status": "running"}
