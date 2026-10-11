"""Phase 0 FastAPI 入口：只暴露 health 接口 + 启动日志。"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings

settings = get_settings()

app = FastAPI(
    title="智能数据分析系统",
    description="自然语言 → 数据分析 → 智能可视化（Phase 0 骨架版）",
    version="0.1.0-phase0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "version": "phase0",
        "phase": "骨架已就绪，后续 phase 接入 LLM/会话/可视化",
    }


@app.get("/")
def root() -> dict:
    return {"service": "smart-data-analysis", "phase": "0", "docs": "/docs"}
