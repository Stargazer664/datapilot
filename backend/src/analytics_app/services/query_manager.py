from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from analytics_app.domain.models import ProgressEvent, ProviderName, QueryRequest, QueryResult
from analytics_app.llm.providers import OpenAICompatibleProvider
from analytics_app.runtime import RuntimeConfigStore
from analytics_app.storage.repositories import AuditRepository, SessionRepository
from analytics_app.workflow.graph import AnalyticsWorkflow


@dataclass
class QueryRun:
    id: str
    request: QueryRequest
    provider: ProviderName
    model: str
    status: str = "queued"
    events: list[ProgressEvent] = field(default_factory=list)
    result: QueryResult | None = None
    signal: asyncio.Event = field(default_factory=asyncio.Event)
    task: asyncio.Task[None] | None = None


class QueryManager:
    def __init__(
        self, runtime: RuntimeConfigStore, sessions: SessionRepository, audit: AuditRepository
    ) -> None:
        self.runtime = runtime
        self.sessions = sessions
        self.audit = audit
        self.runs: dict[str, QueryRun] = {}

    async def create(self, request: QueryRequest) -> QueryRun:
        if not self.sessions.get(request.session_id):
            raise ValueError("会话不存在")
        if not self.runtime.database:
            raise ValueError("请先配置 PostgreSQL")
        provider = request.provider or self.runtime.default_provider
        config = self.runtime.providers[provider]
        if request.model:
            config = config.model_copy(update={"model": request.model})
        query_id = str(uuid4())
        run = QueryRun(id=query_id, request=request, provider=provider, model=config.model)
        self.runs[query_id] = run
        self.sessions.add_message(request.session_id, "user", request.question)
        self.audit.start(
            query_id, request.session_id, provider.value, config.model, request.question
        )
        run.task = asyncio.create_task(self._execute(run, config))
        return run

    async def _emit(self, run: QueryRun, event_type: str, node: str, data: dict[str, Any]) -> None:
        labels = {
            "agent_started": "开始处理",
            "agent_completed": "处理完成",
            "agent_failed": "处理失败",
            "waiting_for_clarification": "等待补充信息",
            "workflow_completed": "分析完成",
            "workflow_failed": "分析失败",
            "cancelled": "任务已取消",
        }
        event = ProgressEvent(
            type=event_type,
            query_id=run.id,
            node=node,
            message=labels.get(event_type),
            data=data,
        )
        run.events.append(event)
        run.signal.set()

    async def _execute(self, run: QueryRun, provider_config: Any) -> None:
        started = time.perf_counter()
        run.status = "running"
        try:
            session = self.sessions.get(run.request.session_id) or {"messages": []}
            history = [
                {"role": item["role"], "content": item["content"]}
                for item in session.get("messages", [])[:-1]
            ]
            llm = OpenAICompatibleProvider(run.provider, provider_config)

            async def progress(event_type: str, node: str, data: dict[str, Any]) -> None:
                await self._emit(run, event_type, node, data)

            workflow = AnalyticsWorkflow(llm, self.runtime.database, progress)  # type: ignore[arg-type]
            state = await workflow.run(
                query_id=run.id,
                session_id=run.request.session_id,
                question=run.request.question,
                history=history,
            )
            payload = state.get("result", {"status": "failed", "error": "工作流未返回结果"})
            run.result = QueryResult(query_id=run.id, **payload)
            run.status = run.result.status
            if run.result.answer:
                self.sessions.add_message(run.request.session_id, "assistant", run.result.answer)
            self.audit.finish(
                run.id,
                status=run.status,
                sql=run.result.sql,
                row_count=len(run.result.rows),
                repair_count=state.get("repair_count", 0),
                duration_ms=round((time.perf_counter() - started) * 1000),
                error_code="workflow_failed" if run.status == "failed" else None,
            )
        except asyncio.CancelledError:
            run.status = "cancelled"
            run.result = QueryResult(query_id=run.id, status="cancelled", error="任务已取消")
            await self._emit(run, "cancelled", "workflow", {})
            self.audit.finish(
                run.id,
                status="cancelled",
                sql=None,
                row_count=0,
                repair_count=0,
                duration_ms=round((time.perf_counter() - started) * 1000),
                error_code="cancelled",
            )
        except Exception:
            run.status = "failed"
            safe_message = "分析任务执行失败，请检查数据库和模型配置。"
            run.result = QueryResult(query_id=run.id, status="failed", error=safe_message)
            await self._emit(run, "workflow_failed", "workflow", {"error": safe_message})
            self.audit.finish(
                run.id,
                status="failed",
                sql=None,
                row_count=0,
                repair_count=0,
                duration_ms=round((time.perf_counter() - started) * 1000),
                error_code="unexpected_error",
            )
        finally:
            run.signal.set()

    def get(self, query_id: str) -> QueryRun:
        if query_id not in self.runs:
            raise KeyError(query_id)
        return self.runs[query_id]

    async def cancel(self, query_id: str) -> None:
        run = self.get(query_id)
        if run.task and not run.task.done():
            run.task.cancel()

    async def events(self, query_id: str) -> AsyncIterator[str]:
        run = self.get(query_id)
        cursor = 0
        while True:
            while cursor < len(run.events):
                event = run.events[cursor]
                cursor += 1
                yield f"event: {event.type}\ndata: {event.model_dump_json()}\n\n"
            if run.status in {"completed", "failed", "cancelled", "waiting_for_clarification"}:
                break
            run.signal.clear()
            try:
                await asyncio.wait_for(run.signal.wait(), timeout=15)
            except TimeoutError:
                yield ": keep-alive\n\n"

    def export_csv(self, query_id: str) -> str:
        import csv
        import io

        run = self.get(query_id)
        if not run.result or run.result.status != "completed":
            raise ValueError("查询尚未完成")
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(run.result.columns)
        writer.writerows(run.result.rows)
        return "\ufeff" + output.getvalue()
