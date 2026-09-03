from collections.abc import AsyncIterator
from typing import Any

import pytest

from analytics_app.agents.contracts import (
    AnalysisPlan,
    AnalysisResult,
    ChartDecision,
    ReviewResult,
    SqlCandidate,
)
from analytics_app.db.executor import ExecutionResult
from analytics_app.domain.models import DatabaseConfigInput
from analytics_app.llm.base import LLMProvider
from analytics_app.workflow.graph import AnalyticsWorkflow


class FakeProvider(LLMProvider):
    @property
    def metadata(self) -> dict[str, Any]:
        return {"provider": "fake"}

    async def complete(self, messages: list[dict[str, str]]) -> str:
        return "ok"

    async def stream(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        yield "ok"

    async def complete_json(self, messages: list[dict[str, str]], schema: type[Any]) -> Any:
        values = {
            AnalysisPlan: AnalysisPlan(intent="query", objective="统计销售额", metrics=["销售额"]),
            SqlCandidate: SqlCandidate(
                sql="SELECT sum(total) AS revenue FROM orders", intent="统计销售额"
            ),
            ReviewResult: ReviewResult(approved=True, reason="语义正确"),
            AnalysisResult: AnalysisResult(answer="销售额为 100。", facts=["销售额为 100"]),
            ChartDecision: ChartDecision(suitable=False, reason="单个指标无需图表"),
        }
        return values[schema]


@pytest.mark.asyncio
async def test_workflow_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_schema(_config: DatabaseConfigInput) -> list[dict[str, Any]]:
        return [
            {
                "schema": "public",
                "table": "orders",
                "columns": [{"name": "total", "type": "numeric"}],
            }
        ]

    async def fake_execute(_config: DatabaseConfigInput, _sql: str) -> ExecutionResult:
        return ExecutionResult(columns=["revenue"], rows=[[100]], truncated=False)

    monkeypatch.setattr("analytics_app.agents.nodes.read_schema", fake_schema)
    monkeypatch.setattr("analytics_app.workflow.graph.execute_readonly", fake_execute)
    events: list[str] = []

    async def progress(event_type: str, _node: str, _data: dict[str, Any]) -> None:
        events.append(event_type)

    workflow = AnalyticsWorkflow(
        FakeProvider(),
        DatabaseConfigInput(database="demo", username="reader", password="secret"),
        progress,
    )
    state = await workflow.run(query_id="q1", session_id="s1", question="销售额是多少", history=[])

    assert state["status"] == "completed"
    assert state["result"]["answer"] == "销售额为 100。"
    assert "workflow_completed" in events
