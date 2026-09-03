from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from analytics_app.db.connection import open_connection
from analytics_app.domain.models import DatabaseConfigInput
from analytics_app.sql.validator import validate_readonly_sql, wrap_with_limit


@dataclass
class ExecutionResult:
    columns: list[str]
    rows: list[list[Any]]
    truncated: bool


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, bytes):
        return f"<binary:{len(value)} bytes>"
    return value


async def execute_readonly(config: DatabaseConfigInput, sql: str) -> ExecutionResult:
    validated = validate_readonly_sql(
        sql,
        allowed_schemas=set(config.allowed_schemas),
        allowed_tables=set(config.allowed_tables) or None,
    )
    wrapped = wrap_with_limit(validated.sql, config.max_rows)
    async with open_connection(config) as connection:
        async with connection.transaction():
            async with connection.cursor() as cursor:
                await cursor.execute("SET TRANSACTION READ ONLY")
                await cursor.execute(
                    "SET LOCAL statement_timeout = %s", (config.timeout_seconds * 1000,)
                )
                await cursor.execute(wrapped)
                columns = [column.name for column in cursor.description or []]
                raw_rows = await cursor.fetchall()

    truncated = len(raw_rows) > config.max_rows
    rows = [[_json_value(value) for value in row] for row in raw_rows[: config.max_rows]]
    encoded_size = len(json.dumps(rows, ensure_ascii=False, default=str).encode("utf-8"))
    if encoded_size > config.max_bytes:
        kept: list[list[Any]] = []
        size = 2
        for row in rows:
            row_size = len(json.dumps(row, ensure_ascii=False, default=str).encode("utf-8")) + 1
            if size + row_size > config.max_bytes:
                break
            kept.append(row)
            size += row_size
        rows = kept
        truncated = True
    return ExecutionResult(columns=columns, rows=rows, truncated=truncated)
