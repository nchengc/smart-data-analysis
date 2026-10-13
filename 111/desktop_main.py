# 智能数据分析系统 — 一键启动脚本（PyInstaller 打包用）
# 此脚本被 PyInstaller 打包时作为入口

import os
import sys
import threading
import time
import webview
import uvicorn

# 兼容 PyInstaller 打包后的路径
def resource_path(rel: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


def run_server() -> None:
    # 把打包资源挂到 app（运行时注册）
    from app.main import app
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse

    dist_dir = resource_path("frontend_dist")
    assets_dir = os.path.join(dist_dir, "assets")
    index_html = os.path.join(dist_dir, "index.html")

    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        @app.get("/")
        def _root():
            if os.path.isfile(index_html):
                return FileResponse(index_html)
            return {"message": "前端资源缺失"}
    else:
        @app.get("/")
        def _root():
            return {
                "message": "PyWebView 桌面模式",
                "note": "前端 dist 未打包，请访问 /docs 看 API 文档",
            }

    uvicorn.run(app, host="127.0.0.1", port=18000, log_level="warning")


def main() -> None:
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    time.sleep(2.0)
    webview.create_window(
        title="智能数据分析系统",
        url="http://127.0.0.1:18000",
        width=1400,
        height=900,
    )
    webview.start()


if __name__ == "__main__":
    main()
