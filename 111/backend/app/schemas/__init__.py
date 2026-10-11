"""Pydantic 数据契约：与前端 types/api.ts 对齐。"""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


ChartType = Literal["bar", "line", "pie", "scatter", "table"]


class ChartSpec(BaseModel):
    type: ChartType
    title: Optional[str] = None
    x: Optional[str] = None
    y: Optional[str] = None
    group_by: Optional[str] = None
    agg: Optional[Literal["sum", "avg", "count", "max", "min"]] = None


class ChatRequest(BaseModel):
    session_id: str
    question: str


class ChatChunk(BaseModel):
    """SSE 单个 chunk。"""

    type: Literal["phase", "sql", "data", "chart", "summary", "done", "error"] = "phase"
    payload: Any = None
    elapsed_ms: Optional[int] = None


class SessionCreate(BaseModel):
    title: Optional[str] = None


class SessionPatch(BaseModel):
    title: str


class SessionOut(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str


class MessageOut(BaseModel):
    id: int
    session_id: str
    role: str
    content: str
    chart: Optional[ChartSpec] = None
    sql: Optional[str] = None
    data: Optional[list[dict[str, Any]]] = None
    created_at: str


class SchemaOut(BaseModel):
    tables: list[str]
    schema_text: str
    row_counts: dict[str, int] = Field(default_factory=dict)
