"""启动时初始化数据库：建表 + 灌入示例数据 + 建 sessions/messages 表。"""

import sqlite3
from pathlib import Path

from app.config import get_settings
from app.db.engine import get_engine

_settings = get_settings()


def init_database() -> None:
    """初始化业务数据库 + 会话存储数据库。

    设计：
    - 业务 DB（customers/products/orders/categories）走 SQLAlchemy
    - 会话 DB（sessions/messages）也走 SQLite 但表结构独立
    二者可以用同一个物理文件（不同表），也可以分开。本期用同一个文件。
    """
    db_path = Path(_settings.sqlite_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    seed_sql = (Path(__file__).parent.parent.parent / "data" / "seed.sql").read_text(
        encoding="utf-8"
    )

    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript(seed_sql)

        # 业务表插入示例数据
        from app.db.seed_data import seed_business_data  # noqa: PLC0415
        seed_business_data(conn)

        # 会话表
        from app.db import session_store  # noqa: PLC0415
        session_store.create_tables_if_missing(conn)

        conn.commit()
    finally:
        conn.close()

    # 验证
    eng = get_engine()
    with eng.connect() as c:
        rows = c.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        print(f"  已初始化数据库表: {[r[0] for r in rows]}")
