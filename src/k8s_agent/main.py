from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from k8s_agent.core.config import settings
from k8s_agent.core.logging import setup_logging
from k8s_agent.models.inspection import store
from k8s_agent.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(settings.log_level)
    store.init(db_path=settings.sqlite_path, max_records=settings.inspection_max_records)
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="K8s Diagnosis Agent", lifespan=lifespan)
static_dir = Path(__file__).resolve().parent.parent.parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/health")
async def health():
    return {"status": "ok"}


from k8s_agent.api.chat import router as chat_router
from k8s_agent.api.agents import router as agents_router
from k8s_agent.api.conversations import router as conversations_router
from k8s_agent.api.inspections import router as inspections_router
from k8s_agent.api.pages import router as pages_router
from k8s_agent.api.proxy import router as proxy_router

app.include_router(chat_router)
app.include_router(agents_router)
app.include_router(inspections_router)
app.include_router(pages_router)
app.include_router(conversations_router)
app.include_router(proxy_router)
