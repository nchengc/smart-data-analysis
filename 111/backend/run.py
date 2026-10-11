"""Phase 0+ 一键启动脚本（Windows / macOS / Linux 通用）。

用法：
    cd backend
    python run.py
"""

import uvicorn

from app.config import get_settings


def main() -> None:
    settings = get_settings()
    print("=" * 60)
    print(" 智能数据分析系统 · 后端 (Phase 2 LangChain + SQLite + Qwen3)")
    print("=" * 60)
    print(f" 监听: http://{settings.app_host}:{settings.app_port}")
    print(f" API 文档: http://localhost:{settings.app_port}/docs")
    print(f" 健康检查: http://localhost:{settings.app_port}/api/health")
    print(f" 数据库: {settings.sqlite_path}")
    print(f" 模型: {settings.qwen_chat_model} / {settings.qwen_sql_model}")
    print(" Ctrl+C 停止")
    print("=" * 60)

    # Phase 2 关闭 reload：避免 reload 期间新代码生效不及时
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
