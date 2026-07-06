from contextlib import asynccontextmanager

from fastapi import FastAPI

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


@app.get("/health")
async def health():
    return {"status": "ok"}


from k8s_agent.api.chat import router as chat_router
from k8s_agent.api.inspections import router as inspections_router
from k8s_agent.api.pages import router as pages_router

app.include_router(chat_router)
app.include_router(inspections_router)
app.include_router(pages_router)
