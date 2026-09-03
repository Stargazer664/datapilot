import pytest

from analytics_app.sql.validator import SqlSafetyError, validate_readonly_sql


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT id, total FROM orders ORDER BY total DESC",
        (
            "WITH monthly AS (SELECT date_trunc('month', created_at) AS month, "
            "sum(total) AS revenue FROM orders GROUP BY 1) SELECT * FROM monthly"
        ),
        (
            "SELECT c.name, sum(o.total) FROM customers c JOIN orders o "
            "ON o.customer_id = c.id GROUP BY c.name"
        ),
    ],
)
def test_allows_readonly_queries(sql: str) -> None:
    result = validate_readonly_sql(sql, allowed_schemas={"public"})
    assert result.sql
    assert result.tables


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM orders",
        "UPDATE orders SET total = 0",
        "DROP TABLE orders",
        "SELECT 1; SELECT 2",
        "SELECT pg_read_file('/etc/passwd')",
        "SELECT nextval('orders_id_seq')",
    ],
)
def test_blocks_unsafe_queries(sql: str) -> None:
    with pytest.raises(SqlSafetyError):
        validate_readonly_sql(sql, allowed_schemas={"public"})


def test_blocks_tables_outside_allowlist() -> None:
    with pytest.raises(SqlSafetyError, match="未授权"):
        validate_readonly_sql(
            "SELECT * FROM private.payroll",
            allowed_schemas={"public"},
        )
