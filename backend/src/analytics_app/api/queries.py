from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse, StreamingResponse

from analytics_app.domain.models import QueryAccepted, QueryRequest, QueryResult

router = APIRouter(prefix="/api/queries", tags=["queries"])


@router.post("", response_model=QueryAccepted, status_code=202)
async def create_query(payload: QueryRequest, request: Request) -> QueryAccepted:
    try:
        run = await request.app.state.queries.create(payload)
        return QueryAccepted(query_id=run.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{query_id}", response_model=QueryResult)
async def get_query(query_id: str, request: Request) -> QueryResult:
    try:
        run = request.app.state.queries.get(query_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="查询不存在") from exc
    return run.result or QueryResult(query_id=query_id, status=run.status)


@router.get("/{query_id}/events")
async def get_query_events(query_id: str, request: Request) -> StreamingResponse:
    try:
        request.app.state.queries.get(query_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="查询不存在") from exc
    return StreamingResponse(
        request.app.state.queries.events(query_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/{query_id}/cancel", status_code=202)
async def cancel_query(query_id: str, request: Request) -> dict[str, str]:
    try:
        await request.app.state.queries.cancel(query_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="查询不存在") from exc
    return {"status": "cancelling"}


@router.get("/{query_id}/export.csv", response_class=PlainTextResponse)
async def export_query(query_id: str, request: Request) -> PlainTextResponse:
    try:
        content = request.app.state.queries.export_csv(query_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="查询不存在") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return PlainTextResponse(
        content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="query-{query_id}.csv"'},
    )
