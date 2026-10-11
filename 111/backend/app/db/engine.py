"""SQLAlchemy 只读引擎 + 元数据反射。

Phase 2 中所有 SQL 查询全部走只读引擎，物理隔离写入权限。
"""

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine

from app.config import get_settings

_settings = get_settings()


def get_engine() -> Engine:
    """返回全局只读 SQLite 引擎。"""
    if not hasattr(get_engine, "_engine"):
        url = f"sqlite:///{_settings.sqlite_path}"
        engine = create_engine(
            url,
            connect_args={"check_same_thread": False},
        )

        @event.listens_for(engine, "connect")
        def _set_readonly(dbapi_conn, _record):  # noqa: ANN001
            # 物理级只读：即使 SQL 写错 SQLite 也直接报错
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA query_only = ON")
            cursor.close()

        get_engine._engine = engine  # type: ignore[attr-defined]
    return get_engine._engine  # type: ignore[attr-defined]


def reset_engine_cache() -> None:
    """测试 / 重置场景下丢弃现有引擎（强制重新连接）。"""
    eng = getattr(get_engine, "_engine", None)
    if eng is not None:
        eng.dispose()
    if hasattr(get_engine, "_engine"):
        delattr(get_engine, "_engine")
