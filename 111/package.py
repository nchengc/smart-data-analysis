# 智能数据分析系统 — 一体化打包脚本
#
# 目标：把 FastAPI 后端 + Vite 前端打包成一个可双击启动的桌面应用
# 方案：使用 PyWebView（轻量级 WebKit/WebView2），无需 Electron 大体积
#
# pip install pywebview pyinstaller
# python package.py  →  产出 dist/SmartDataAnalysis.exe
#
# 工作原理：
# 1. 启动时用 pywebview 启动一个桌面窗口（无浏览器界面）
# 2. 后端 FastAPI 在子进程启动（python -m uvicorn）
# 3. 前端读打包好的 dist 资源挂到 FastAPI 上 (StaticFiles)
# 4. pywebview 加载 http://localhost:8000

from __future__ import annotations

import os
import sys
import threading
import time
import webview
import uvicorn

from app.main import app  # FastAPI 实例
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse


FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "frontend_dist")
INDEX_HTML = os.path.join(FRONTEND_DIST, "index.html")


def mount_frontend() -> None:
    """把打包好的前端资源挂到根路径。"""
    if not os.path.exists(FRONTEND_DIST):
        print(f"  [warn] 前端 dist 目录不存在：{FRONTEND_DIST}")
        print("  [warn] 仅后端界面可访问；前端访问 http://localhost:8000/")
        return
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

    @app.get("/")
    def root():
        if os.path.exists(INDEX_HTML):
            return FileResponse(INDEX_HTML)
        return {"message": "请先 build 前端：cd frontend && npm run build"}


def run_server() -> None:
    """在独立线程跑 FastAPI 服务（不开 reload）。"""
    mount_frontend()
    uvicorn.run(
        app,
        host="127.0.0.1",   # 仅 localhost，避免安全告警
        port=18000,
        log_level="warning",
    )


def main() -> None:
    # 1) 启动后端
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    time.sleep(2.0)  # 给 uvicorn 时间启动

    # 2) 打开桌面窗口
    webview.create_window(
        title="智能数据分析系统",
        url="http://127.0.0.1:18000",
        width=1400,
        height=900,
        resizable=True,
        fullscreen=False,
    )
    webview.start()


if __name__ == "__main__":
    main()
