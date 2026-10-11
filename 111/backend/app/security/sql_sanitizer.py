"""SQL 安全校验：sqlparse AST 白名单 + 关键字黑名单 + 强制 LIMIT。"""


class SQLSecurityError(Exception):
    pass


_FORBIDDEN_DDL = {
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE",
    "CREATE", "REPLACE", "ATTACH", "DETACH", "PRAGMA", "VACUUM",
    "REINDEX", "BEGIN", "COMMIT", "ROLLBACK",
}
_FORBIDDEN_FUNCTIONS = {"LOAD_EXTENSION", "RANDOMBLOB"}  # 任何具有副作用的函数


def _upper_tokens(sql: str) -> list[str]:
    import re
    return re.findall(r"[A-Za-z_]+", sql.upper())


def validate_select_only(sql: str) -> str:
    """保证 SQL 是单条 SELECT，禁止任何 DDL/DML。"""
    if not sql or not sql.strip():
        raise SQLSecurityError("SQL 不能为空")

    try:
        import sqlparse
    except ImportError as e:
        raise SQLSecurityError("需要 sqlparse 包") from e

    parsed = sqlparse.parse(sql)
    if len(parsed) != 1:
        raise SQLSecurityError("仅允许单条 SQL")

    stmt = parsed[0]
    stmt_type = (stmt.get_type() or "").upper()
    if stmt_type != "SELECT":
        raise SQLSecurityError(f"只允许 SELECT，禁止 {stmt_type or '其他'} 语句")

    tokens = _upper_tokens(sql)
    for kw in _FORBIDDEN_DDL:
        if kw in tokens:
            raise SQLSecurityError(f"禁止关键字：{kw}")

    for fn in _FORBIDDEN_FUNCTIONS:
        if fn in tokens:
            raise SQLSecurityError(f"禁止函数：{fn}")

    return sql


def ensure_limit(sql: str, default_limit: int = 1000) -> str:
    """若 SQL 没有 LIMIT，自动追加（防止返回几十万行）。"""
    upper = sql.upper()
    if "LIMIT" in upper:
        return sql
    return sql.rstrip().rstrip(";") + f" LIMIT {default_limit}"


def normalize_sql(sql: str) -> str:
    """标准化：去掉多余空白、统一结尾。"""
    import sqlparse as _sqlparse
    formatted = _sqlparse.format(sql, reindent=False, keyword_case="lower", identifier_case=None)
    formatted = formatted.strip().rstrip(";")
    return formatted
