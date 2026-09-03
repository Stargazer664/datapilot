from __future__ import annotations

import json
from typing import Any

from analytics_app.agents.contracts import (
    AnalysisPlan,
    AnalysisResult,
    ChartDecision,
    ReviewResult,
    SqlCandidate,
)
from analytics_app.agents.prompts import (
    ANALYSIS_SYSTEM,
    COORDINATOR_SYSTEM,
    REVIEWER_SYSTEM,
    SQL_SYSTEM,
    VISUALIZATION_SYSTEM,
)
from analytics_app.charts.validator import ChartValidationError, validate_plotly_spec
from analytics_app.db.schema_reader import rank_schema, read_schema
from analytics_app.domain.models import DatabaseConfigInput
from analytics_app.llm.base import LLMProvider


def _messages(system: str, payload: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False, default=str)},
    ]


class CoordinatorAgent:
    def __init__(self, llm: LLMProvider) -> None:
        self.llm = llm

    async def run(self, question: str, history: list[dict[str, str]]) -> AnalysisPlan:
        return await self.llm.complete_json(
            _messages(COORDINATOR_SYSTEM, {"question": question, "recent_history": history[-6:]}),
            AnalysisPlan,
        )


class SchemaAgent:
    def __init__(self, config: DatabaseConfigInput) -> None:
        self.config = config

    async def run(self, question: str) -> list[dict[str, Any]]:
        schema = await read_schema(self.config)
        return rank_schema(question, schema)


class SqlAgent:
    def __init__(self, llm: LLMProvider) -> None:
        self.llm = llm

    async def run(
        self,
        question: str,
        plan: AnalysisPlan,
        schema: list[dict[str, Any]],
        feedback: str | None,
    ) -> SqlCandidate:
        return await self.llm.complete_json(
            _messages(
                SQL_SYSTEM,
                {
                    "question": question,
                    "plan": plan.model_dump(),
                    "schema": schema,
                    "repair_feedback": feedback,
                },
            ),
            SqlCandidate,
        )


class SqlReviewerAgent:
    def __init__(self, llm: LLMProvider) -> None:
        self.llm = llm

    async def run(
        self,
        question: str,
        plan: AnalysisPlan,
        schema: list[dict[str, Any]],
        candidate: SqlCandidate,
    ) -> ReviewResult:
        return await self.llm.complete_json(
            _messages(
                REVIEWER_SYSTEM,
                {
                    "question": question,
                    "plan": plan.model_dump(),
                    "schema": schema,
                    "candidate": candidate.model_dump(),
                },
            ),
            ReviewResult,
        )


class AnalysisAgent:
    def __init__(self, llm: LLMProvider) -> None:
        self.llm = llm

    async def run(
        self,
        question: str,
        columns: list[str],
        rows: list[list[Any]],
        truncated: bool,
    ) -> AnalysisResult:
        return await self.llm.complete_json(
            _messages(
                ANALYSIS_SYSTEM,
                {
                    "question": question,
                    "columns": columns,
                    "rows": rows[:200],
                    "row_count_sent": min(len(rows), 200),
                    "truncated": truncated or len(rows) > 200,
                },
            ),
            AnalysisResult,
        )


class VisualizationAgent:
    def __init__(self, llm: LLMProvider) -> None:
        self.llm = llm

    async def run(
        self,
        question: str,
        columns: list[str],
        rows: list[list[Any]],
        analysis: AnalysisResult,
    ) -> dict[str, Any] | None:
        decision = await self.llm.complete_json(
            _messages(
                VISUALIZATION_SYSTEM,
                {
                    "question": question,
                    "columns": columns,
                    "rows": rows[:100],
                    "analysis": analysis.model_dump(),
                },
            ),
            ChartDecision,
        )
        if not decision.suitable or not decision.chart:
            return None
        try:
            return validate_plotly_spec(decision.chart)
        except ChartValidationError:
            return None
