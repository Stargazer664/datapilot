from __future__ import annotations

from typing import Any, TypedDict

from analytics_app.agents.contracts import AnalysisPlan, AnalysisResult, ReviewResult, SqlCandidate


class AgentState(TypedDict, total=False):
    query_id: str
    session_id: str
    question: str
    history: list[dict[str, str]]
    plan: AnalysisPlan
    schema: list[dict[str, Any]]
    sql_candidate: SqlCandidate
    review: ReviewResult
    repair_count: int
    validation_error: str | None
    execution_error: str | None
    columns: list[str]
    rows: list[list[Any]]
    truncated: bool
    analysis: AnalysisResult
    chart: dict[str, Any] | None
    status: str
    error: str | None
    result: dict[str, Any]
