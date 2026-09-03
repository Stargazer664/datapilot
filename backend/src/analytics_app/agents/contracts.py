from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class AnalysisPlan(BaseModel):
    intent: Literal["query", "clarify", "unsupported"] = "query"
    objective: str
    dimensions: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    filters: list[str] = Field(default_factory=list)
    time_grain: str | None = None
    clarification_question: str | None = None


class SqlCandidate(BaseModel):
    sql: str
    intent: str
    field_explanations: dict[str, str] = Field(default_factory=dict)
    expected_columns: list[str] = Field(default_factory=list)


class ReviewResult(BaseModel):
    approved: bool
    reason: str
    suggestions: list[str] = Field(default_factory=list)


class AnalysisResult(BaseModel):
    answer: str
    facts: list[str] = Field(default_factory=list)
    inferences: list[str] = Field(default_factory=list)
    data_sufficient: bool = True


class ChartDecision(BaseModel):
    suitable: bool
    reason: str
    chart: dict[str, Any] | None = None
