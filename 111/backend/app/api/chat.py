"""/api/chat · 流式（SSE）问答接口。"""

from __future__ import annotations

import asyncio
import json
import queue
import threading
from typing import Iterator

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from app.agents.runner import run_chat
from app.schemas import ChatRequest

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _run_in_thread(question_text: str, sid: str, q: queue.Queue) -> None:
    """在工作线程跑 run_chat，通过 queue 把事件回给 SSE 生成器。"""
    try:
        q.put({"type": "phase", "payload": "正在理解问题并检索 Schema…"})
        result = run_chat(sid, question_text)
        q.put({"type": "mode", "payload": result.mode})
        q.put({"type": "sql", "payload": result.sql})
        q.put({"type": "data", "payload": {"rows": result.data, "row_count": result.row_count}})
        q.put({"type": "chart", "payload": result.chart})
        q.put({"type": "summary", "payload": {"summary": result.summary}})
        if result.error:
            q.put({"type": "error", "payload": result.error})
        q.put({"type": "done", "payload": {"elapsed_ms": result.elapsed_ms, "rounds": result.reflection_rounds}})
    except Exception as e:
        q.put({"type": "error", "payload": str(e)})
        q.put({"type": "done", "payload": None})
    finally:
        q.put(None)  # sentinel


def _event_iter(q: queue.Queue) -> Iterator[dict]:
    while True:
        ev = q.get()
        if ev is None:
            return
        yield {"event": ev["type"], "data": json.dumps(ev, ensure_ascii=False, default=str)}


@router.post("/stream")
async def stream_chat(req: ChatRequest) -> EventSourceResponse:
    q: queue.Queue = queue.Queue(maxsize=128)
    t = threading.Thread(
        target=_run_in_thread, args=(req.question, req.session_id, q), daemon=True
    )
    t.start()
    # 把同步迭代器包装成异步
    async def gen():
        loop = asyncio.get_event_loop()
        gen_iter = _event_iter(q)
        while True:
            ev = await loop.run_in_executor(None, _next_or_done, gen_iter)
            if ev is None:
                break
            yield ev

    return EventSourceResponse(gen())


def _next_or_done(gen_iter: Iterator) -> dict | None:
    try:
        return next(gen_iter)
    except StopIteration:
        return None
