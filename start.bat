@echo off
chcp 65001
setlocal

echo ============================================================
echo   智能数据分析系统  Phase 0 · 一键启动
echo ============================================================
echo.

set ROOT=%~dp0

REM ---------- 后端 ----------
echo [1/2] 启动 FastAPI 后端 (port 8000)...
start "smart-data-backend" cmd /k "cd /d %ROOT%backend && python run.py"

REM ---------- 前端 ----------
echo [2/2] 启动 Vite 前端 (port 5173)...
start "smart-data-frontend" cmd /k "cd /d %ROOT%frontend && npm run dev"

echo.
echo ============================================================
echo   两个窗口已弹出：
echo    后端 → http://localhost:8000/api/health
echo    前端 → http://localhost:5173
echo ============================================================
echo.
pause
