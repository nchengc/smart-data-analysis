"""用 LangChain 的 SQLDatabase 反射业务库的 schema。"""

from langchain_community.utilities import SQLDatabase

from app.config import get_settings

_settings = get_settings()


def get_sql_database() -> SQLDatabase:
    """返回 LangChain 的 SQLDatabase 包装（含全部表 DDL）。"""
    if not hasattr(get_sql_database, "_db"):
        get_sql_database._db = SQLDatabase.from_uri(  # type: ignore[attr-defined]
            f"sqlite:///{_settings.sqlite_path}",
            sample_rows_in_table_info=2,
        )
    return get_sql_database._db  # type: ignore[attr-defined]


def get_schema_text() -> str:
    """返回完整 schema 文本，可用于 system prompt 注入。"""
    db = get_sql_database()
    return db.get_table_info()


def list_tables() -> list[str]:
    db = get_sql_database()
    return list(db.get_usable_table_names())
