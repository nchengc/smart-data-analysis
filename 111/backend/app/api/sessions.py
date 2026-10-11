"""/api/sessions 系列接口。"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Body, HTTPException

from app.db import session_store
from app.schemas import MessageOut, SessionCreate, SessionOut, SessionPatch

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("", response_model=list[SessionOut])
def list_sessions() -> list[dict[str, Any]]:
    return session_store.list_sessions()


@router.post("", response_model=SessionOut, status_code=201)
def create_session(body: SessionCreate) -> dict[str, Any]:
    """前端必须发 JSON body（可以是空对象 `{}`），title 可省略。"""
    title = (body.title if body and body.title else "新会话").strip() or "新会话"
    s = session_store.create_session(title=title)
    return {
        "id": s.id,
        "title": s.title,
        "created_at": s.created_at,
        "updated_at": s.updated_at,
    }


@router.get("/{session_id}", response_model=SessionOut)
def get_session(session_id: str) -> dict[str, Any]:
    s = session_store.get_session(session_id)
    if not s:
        raise HTTPException(404, "会话不存在")
    return {
        "id": s.id,
        "title": s.title,
        "created_at": s.created_at,
        "updated_at": s.updated_at,
    }


@router.patch("/{session_id}", response_model=SessionOut)
def rename_session(session_id: str, body: SessionPatch) -> dict[str, Any]:
    ok = session_store.rename_session(session_id, body.title.strip() or "未命名")
    if not ok:
        raise HTTPException(404, "会话不存在")
    s = session_store.get_session(session_id)
    return {
        "id": s.id,
        "title": s.title,
        "created_at": s.created_at,
        "updated_at": s.updated_at,
    }


@router.delete("/{session_id}")
def delete_session(session_id: str) -> dict[str, Any]:
    ok = session_store.delete_session(session_id)
    if not ok:
        raise HTTPException(404, "会话不存在")
    return {"deleted": True}


@router.get("/{session_id}/messages", response_model=list[MessageOut])
def list_messages(session_id: str, limit: int = 50) -> list[dict[str, Any]]:
    if not session_store.get_session(session_id):
        raise HTTPException(404, "会话不存在")
    return session_store.list_messages(session_id, limit=limit)
