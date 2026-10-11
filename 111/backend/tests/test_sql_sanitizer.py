"""SQL 安全层单元测试。

覆盖：
- 正常 SELECT 通过
- 多语句拒绝
- 危险关键字拒绝（INSERT/UPDATE/DELETE/DROP...）
- 危险函数拒绝（load_extension 等）
- LIMIT 强制注入
- normalize_sql
"""

import pytest

from app.security.sql_sanitizer import (
    SQLSecurityError,
    ensure_limit,
    normalize_sql,
    validate_select_only,
)


VALID_SQL = [
    "SELECT * FROM orders",
    "SELECT region, SUM(total_amount) FROM orders GROUP BY region",
    "SELECT strftime('%Y-%m', order_date) AS ym, COUNT(*) FROM orders GROUP BY ym",
    "WITH t AS (SELECT * FROM customers) SELECT * FROM t",
]


FORBIDDEN_SQL = [
    "INSERT INTO customers VALUES (1, 'a', 'b', 'c', 'd', 'e')",
    "DELETE FROM orders",
    "UPDATE customers SET name='x'",
    "DROP TABLE orders",
    "ALTER TABLE orders ADD COLUMN x TEXT",
    "PRAGMA writable_schema = ON",
    "ATTACH DATABASE 'evil.db' AS evil",
    "SELECT load_extension('evil')",
    "SELECT 1; DROP TABLE orders",
    "",
    "   ",
    "TRUNCATE orders",
    "VACUUM",
]


@pytest.mark.parametrize("sql", VALID_SQL)
def test_valid_select_passes(sql: str) -> None:
    validate_select_only(sql)


@pytest.mark.parametrize("sql", FORBIDDEN_SQL)
def test_forbidden_sql_rejected(sql: str) -> None:
    with pytest.raises(SQLSecurityError):
        validate_select_only(sql)


def test_ensure_limit_appends() -> None:
    sql = "SELECT * FROM orders"
    out = ensure_limit(sql, default_limit=50)
    assert "LIMIT 50" in out.upper()


def test_ensure_limit_preserves_existing() -> None:
    sql = "SELECT * FROM orders LIMIT 10"
    out = ensure_limit(sql)
    assert out == sql


def test_normalize_strips_trailing_semicolon() -> None:
    out = normalize_sql("SELECT 1;")
    assert not out.endswith(";")
