from typing import Any, cast

from fastapi import APIRouter, HTTPException, Request

from analytics_app.domain.models import SessionCreate, SessionRecord
from analytics_app.storage.repositories import SessionRepository

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", response_model=SessionRecord)
async def create_session(payload: SessionCreate, request: Request) -> SessionRecord:
    repository = cast(SessionRepository, request.app.state.sessions)
    return repository.create(payload.title)


@router.get("/{session_id}")
async def get_session(session_id: str, request: Request) -> dict[str, Any]:
    repository = cast(SessionRepository, request.app.state.sessions)
    result = repository.get(session_id)
    if not result:
        raise HTTPException(status_code=404, detail="会话不存在")
    return result
