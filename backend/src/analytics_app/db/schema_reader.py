from __future__ import annotations

from collections import defaultdict
from typing import Any

from analytics_app.db.connection import open_connection
from analytics_app.domain.models import DatabaseConfigInput


async def read_schema(config: DatabaseConfigInput) -> list[dict[str, Any]]:
    sql = """
    SELECT c.table_schema, c.table_name, c.column_name, c.data_type, c.is_nullable,
           pgd.description AS column_comment
    FROM information_schema.columns c
    LEFT JOIN pg_catalog.pg_class pc ON pc.relname = c.table_name
    LEFT JOIN pg_catalog.pg_namespace pn ON pn.oid = pc.relnamespace
        AND pn.nspname = c.table_schema
    LEFT JOIN pg_catalog.pg_attribute pa ON pa.attrelid = pc.oid
        AND pa.attname = c.column_name
    LEFT JOIN pg_catalog.pg_description pgd ON pgd.objoid = pc.oid
        AND pgd.objsubid = pa.attnum
    WHERE c.table_schema = ANY(%s)
    ORDER BY c.table_schema, c.table_name, c.ordinal_position
    """
    async with open_connection(config) as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(sql, (config.allowed_schemas,))
            rows = await cursor.fetchall()

    tables: dict[str, dict[str, Any]] = defaultdict(dict)
    for schema, table, column, data_type, nullable, comment in rows:
        qualified = f"{schema}.{table}"
        if (
            config.allowed_tables
            and qualified not in config.allowed_tables
            and table not in config.allowed_tables
        ):
            continue
        if column in config.blocked_columns or f"{qualified}.{column}" in config.blocked_columns:
            continue
        tables.setdefault(qualified, {"schema": schema, "table": table, "columns": []})
        tables[qualified]["columns"].append(
            {
                "name": column,
                "type": data_type,
                "nullable": nullable == "YES",
                "comment": comment,
            }
        )
    return list(tables.values())


def rank_schema(
    question: str, tables: list[dict[str, Any]], limit: int = 12
) -> list[dict[str, Any]]:
    terms = {token.lower() for token in question.replace("_", " ").split() if len(token) > 1}

    def score(table: dict[str, Any]) -> tuple[int, str]:
        searchable = " ".join(
            [table["table"]]
            + [column["name"] for column in table["columns"]]
            + [column.get("comment") or "" for column in table["columns"]]
        ).lower()
        return (
            sum(2 if term in table["table"].lower() else 1 for term in terms if term in searchable),
            table["table"],
        )

    ranked = sorted(tables, key=score, reverse=True)
    positive = [table for table in ranked if score(table)[0] > 0]
    return (positive or ranked)[:limit]
