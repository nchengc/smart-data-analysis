"""会话存储：sessions + messages 两张表，全部本地 SQLite。

会话与业务数据共用一个 SQLite 文件（不同表），本地化部署简单。
"""

import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from app.config import get_settings

_settings = get_settings()


@dataclass
class Session:
    id: str
    title: str
    created_at: str
    updated_at: str
    context_summary: str = ""


@dataclass
class Message:
    id: int
    session_id: str
    role: str  # 'user' | 'assistant'
    content: str
    chart_json: Optional[str] = None
    sql_text: Optional[str] = None
    data_json: Optional[str] = None
    created_at: str = ""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_settings.sqlite_path)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables_if_missing(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id              TEXT PRIMARY KEY,
            title           TEXT NOT NULL DEFAULT '新会话',
            created_at      TEXT NOT NULL,
            updated_at      TEXT NOT NULL,
            context_summary TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS messages (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  TEXT NOT NULL,
            role        TEXT NOT NULL,
            content     TEXT NOT NULL,
            chart_json  TEXT,
            sql_text    TEXT,
            data_json   TEXT,
            created_at  TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
        """
    )


def create_session(title: str = "新会话") -> Session:
    sid = f"s_{uuid.uuid4().hex[:12]}"
    now = datetime.utcnow().isoformat(timespec="seconds")
    conn = _connect()
    try:
        create_tables_if_missing(conn)
        conn.execute(
            "INSERT INTO sessions (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (sid, title, now, now),
        )
        conn.commit()
    finally:
        conn.close()
    return Session(id=sid, title=title, created_at=now, updated_at=now)


def list_sessions() -> list[dict[str, Any]]:
    conn = _connect()
    try:
        create_tables_if_missing(conn)
        rows = conn.execute(
            "SELECT id, title, created_at, updated_at FROM sessions ORDER BY updated_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_session(sid: str) -> Optional[Session]:
    conn = _connect()
    try:
        create_tables_if_missing(conn)
        r = conn.execute(
            "SELECT id, title, created_at, updated_at, context_summary FROM sessions WHERE id=?",
            (sid,),
        ).fetchone()
        if not r:
            return None
        return Session(**dict(r))
    finally:
        conn.close()


def rename_session(sid: str, new_title: str) -> bool:
    conn = _connect()
    try:
        cur = conn.execute(
            "UPDATE sessions SET title=?, updated_at=? WHERE id=?",
            (new_title, datetime.utcnow().isoformat(timespec="seconds"), sid),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def touch_session(sid: str) -> None:
    """更新会话 updated_at。"""
    conn = _connect()
    try:
        conn.execute(
            "UPDATE sessions SET updated_at=? WHERE id=?",
            (datetime.utcnow().isoformat(timespec="seconds"), sid),
        )
        conn.commit()
    finally:
        conn.close()


def delete_session(sid: str) -> bool:
    conn = _connect()
    try:
        cur = conn.execute("DELETE FROM sessions WHERE id=?", (sid,))
        conn.execute("DELETE FROM messages WHERE session_id=?", (sid,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def append_message(
    session_id: str,
    role: str,
    content: str,
    *,
    chart: Optional[dict[str, Any]] = None,
    sql: Optional[str] = None,
    data: Optional[list[dict[str, Any]]] = None,
) -> Message:
    now = datetime.utcnow().isoformat(timespec="seconds")
    conn = _connect()
    try:
        create_tables_if_missing(conn)
        cur = conn.execute(
            """INSERT INTO messages (session_id, role, content, chart_json, sql_text, data_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                session_id,
                role,
                content,
                json.dumps(chart, ensure_ascii=False) if chart else None,
                sql,
                json.dumps(data, ensure_ascii=False) if data else None,
                now,
            ),
        )
        msg_id = cur.lastrowid
        conn.execute(
            "UPDATE sessions SET updated_at=? WHERE id=?",
            (now, session_id),
        )
        conn.commit()
    finally:
        conn.close()
    return Message(
        id=msg_id,
        session_id=session_id,
        role=role,
        content=content,
        chart_json=json.dumps(chart, ensure_ascii=False) if chart else None,
        sql_text=sql,
        data_json=json.dumps(data, ensure_ascii=False) if data else None,
        created_at=now,
    )


def list_messages(session_id: str, limit: int = 20) -> list[dict[str, Any]]:
    """最近 limit 条消息，按时间升序。"""
    conn = _connect()
    try:
        rows = conn.execute(
            """SELECT id, role, content, chart_json, sql_text, data_json, created_at
               FROM (
                 SELECT * FROM messages WHERE session_id=?
                 ORDER BY id DESC LIMIT ?
               ) ORDER BY id ASC""",
            (session_id, limit),
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            if d.get("chart_json"):
                try:
                    d["chart"] = json.loads(d["chart_json"])
                except Exception:
                    d["chart"] = None
            if d.get("data_json"):
                try:
                    d["data"] = json.loads(d["data_json"])
                except Exception:
                    d["data"] = None
            out.append(d)
        return out
    finally:
        conn.close()


def auto_title_from_question(q: str) -> str:
    """把首条用户问题前 18 字当会话标题。"""
    s = (q or "").strip().replace("\n", " ")
    if len(s) > 18:
        s = s[:18] + "…"
    return s or "新会话"


def set_context_summary(session_id: str, summary: str) -> None:
    conn = _connect()
    try:
        conn.execute(
            "UPDATE sessions SET context_summary=? WHERE id=?",
            (summary, session_id),
        )
        conn.commit()
    finally:
        conn.close()
