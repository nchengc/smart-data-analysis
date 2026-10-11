"""返回数据库 schema 元数据。"""

from __future__ import annotations

from fastapi import APIRouter

from app.db.engine import get_engine
from app.db.metadata import get_schema_text, list_tables
from app.schemas import SchemaOut

router = APIRouter(prefix="/api/schema", tags=["schema"])


@router.get("", response_model=SchemaOut)
def get_schema() -> dict:
    eng = get_engine()
    tables = list_tables()
    counts: dict[str, int] = {}
    with eng.connect() as conn:
        for t in tables:
            try:
                r = conn.exec_driver_sql(f"SELECT COUNT(*) FROM {t}").fetchone()
                counts[t] = int(r[0]) if r else 0
            except Exception:
                counts[t] = -1
    return {
        "tables": tables,
        "schema_text": get_schema_text(),
        "row_counts": counts,
    }
