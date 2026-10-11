"""FastAPI 入口：注册所有路由 + 启动时初始化数据库。"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat as chat_api
from app.api import schema as schema_api
from app.api import sessions as sessions_api
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="智能数据分析系统 API",
    description="Phase 2 · 后端业务接口（LangChain + SQLite + Qwen3）",
    version="0.2.0-phase2",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list + ["*"],  # Phase 2 兼容 dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    """启动时初始化数据库（建业务表 + 灌入示例数据 + 会话表）。"""
    if os.environ.get("SDA_SKIP_INIT") == "1":
        return
    try:
        from app.db.init_db import init_database
        init_database()
        print("[startup] 数据库初始化完成")
    except Exception as e:
        print(f"[startup] 数据库初始化失败：{e}")


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "version": "phase2",
        "phase": "LangChain + SQLite + Qwen3 + SSE",
    }


# 注册路由
app.include_router(sessions_api.router)
app.include_router(schema_api.router)
app.include_router(chat_api.router)
