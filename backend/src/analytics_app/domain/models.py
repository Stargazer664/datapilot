from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, SecretStr, field_validator


class ProviderName(StrEnum):
    OPENAI = "openai"
    DEEPSEEK = "deepseek"
    QWEN = "qwen"


class ProviderConfigInput(BaseModel):
    api_key: SecretStr | None = None
    base_url: str | None = None
    model: str
    timeout_seconds: int = Field(default=60, ge=5, le=300)


class ProviderConfigPublic(BaseModel):
    provider: ProviderName
    base_url: str
    model: str
    timeout_seconds: int
    api_key_configured: bool


class DatabaseConfigInput(BaseModel):
    host: str = "localhost"
    port: int = Field(default=5432, ge=1, le=65535)
    database: str
    username: str
    password: SecretStr | None = None
    sslmode: str = "prefer"
    allowed_schemas: list[str] = Field(default_factory=lambda: ["public"])
    allowed_tables: list[str] = Field(default_factory=list)
    blocked_columns: list[str] = Field(default_factory=list)
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    max_rows: int = Field(default=1000, ge=1, le=100_000)
    max_bytes: int = Field(default=5_242_880, ge=1024, le=104_857_600)

    @field_validator("allowed_schemas")
    @classmethod
    def require_schema(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("至少允许一个 Schema")
        return value


class DatabaseConfigPublic(BaseModel):
    host: str
    port: int
    database: str
    username: str
    sslmode: str
    allowed_schemas: list[str]
    allowed_tables: list[str]
    blocked_columns: list[str]
    timeout_seconds: int
    max_rows: int
    max_bytes: int
    password_configured: bool


class SessionCreate(BaseModel):
    title: str = "新分析"


class SessionRecord(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str


class QueryRequest(BaseModel):
    session_id: str
    question: str = Field(min_length=1, max_length=4000)
    provider: ProviderName | None = None
    model: str | None = None


class QueryAccepted(BaseModel):
    query_id: str
    status: str = "queued"


class PlotlySpec(BaseModel):
    data: list[dict[str, Any]]
    layout: dict[str, Any] = Field(default_factory=dict)


class QueryResult(BaseModel):
    query_id: str
    status: str
    answer: str | None = None
    sql: str | None = None
    columns: list[str] = Field(default_factory=list)
    rows: list[list[Any]] = Field(default_factory=list)
    chart: PlotlySpec | None = None
    truncated: bool = False
    error: str | None = None


class ProgressEvent(BaseModel):
    type: str
    query_id: str
    node: str | None = None
    message: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
