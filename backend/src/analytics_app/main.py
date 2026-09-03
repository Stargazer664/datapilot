from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from analytics_app.api.queries import router as queries_router
from analytics_app.api.sessions import router as sessions_router
from analytics_app.api.settings import router as settings_router
from analytics_app.config import settings
from analytics_app.runtime import RuntimeConfigStore
from analytics_app.services.query_manager import QueryManager
from analytics_app.storage.database import LocalDatabase
from analytics_app.storage.repositories import AuditRepository, SessionRepository


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    local_database = LocalDatabase(settings.app_sqlite_path)
    local_database.initialize()
    runtime = RuntimeConfigStore(settings)
    sessions = SessionRepository(local_database)
    audit = AuditRepository(local_database)
    app.state.runtime = runtime
    app.state.sessions = sessions
    app.state.audit = audit
    app.state.queries = QueryManager(runtime, sessions, audit)
    yield


app = FastAPI(title="DataPilot API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(settings_router)
app.include_router(sessions_router)
app.include_router(queries_router)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
