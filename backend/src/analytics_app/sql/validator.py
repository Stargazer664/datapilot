from __future__ import annotations

from dataclasses import dataclass

from sqlglot import exp, parse
from sqlglot.errors import ParseError


class SqlSafetyError(ValueError):
    """Raised when SQL cannot be proven read-only and in policy."""


@dataclass(frozen=True)
class ValidatedSql:
    sql: str
    tables: tuple[str, ...]


_BLOCKED_NODE_TYPES = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Create,
    exp.Drop,
    exp.Alter,
    exp.Command,
    exp.Merge,
    exp.Transaction,
)
_BLOCKED_FUNCTIONS = {
    "dblink",
    "lo_export",
    "nextval",
    "pg_read_binary_file",
    "pg_read_file",
    "pg_sleep",
    "set_config",
}


def validate_readonly_sql(
    sql: str,
    *,
    allowed_schemas: set[str],
    allowed_tables: set[str] | None = None,
) -> ValidatedSql:
    cleaned = sql.strip()
    if not cleaned:
        raise SqlSafetyError("SQL 不能为空")
    try:
        statements = parse(cleaned, read="postgres")
    except ParseError as exc:
        raise SqlSafetyError("SQL 无法解析") from exc
    if len(statements) != 1:
        raise SqlSafetyError("只允许执行一条 SQL")

    statement = statements[0]
    if not isinstance(statement, (exp.Select, exp.Union, exp.Intersect, exp.Except)):
        raise SqlSafetyError("只允许只读 SELECT 查询")
    if any(statement.find(kind) is not None for kind in _BLOCKED_NODE_TYPES):
        raise SqlSafetyError("SQL 包含写入或管理语句")
    if statement.args.get("locks"):
        raise SqlSafetyError("不允许锁定查询")

    for function in statement.find_all(exp.Func):
        name = function.name.lower() if isinstance(function, exp.Anonymous) else ""
        if name in _BLOCKED_FUNCTIONS:
            raise SqlSafetyError(f"不允许调用函数 {name}")

    tables: list[str] = []
    cte_names = {cte.alias_or_name.lower() for cte in statement.find_all(exp.CTE)}
    for table in statement.find_all(exp.Table):
        name = table.name
        schema = table.db or "public"
        if name.lower() in cte_names and not table.db:
            continue
        qualified = f"{schema}.{name}"
        if schema not in allowed_schemas:
            raise SqlSafetyError(f"未授权访问 Schema：{schema}")
        if allowed_tables and qualified not in allowed_tables and name not in allowed_tables:
            raise SqlSafetyError(f"未授权访问数据表：{qualified}")
        tables.append(qualified)

    return ValidatedSql(sql=statement.sql(dialect="postgres"), tables=tuple(dict.fromkeys(tables)))


def wrap_with_limit(sql: str, max_rows: int) -> str:
    return f"SELECT * FROM ({sql.rstrip(';')}) AS _datapilot_safe_query LIMIT {int(max_rows) + 1}"
