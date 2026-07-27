from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
async def root():
    return {
        "service": "K8s Diagnosis Agent",
        "health": "/health",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


from k8s_agent.api.chat import router as chat_router
from k8s_agent.api.agents import router as agents_router
from k8s_agent.api.conversations import router as conversations_router
from k8s_agent.api.inspections import router as inspections_router
from k8s_agent.api.proxy import router as proxy_router

app.include_router(chat_router)
app.include_router(agents_router)
app.include_router(inspections_router)
app.include_router(conversations_router)
app.include_router(proxy_router)
