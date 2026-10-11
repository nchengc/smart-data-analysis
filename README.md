# 智能数据分析系统

> 自然语言提问 → 自动数据分析 → 智能可视化呈现

## 📌 当前进度

| Phase | 状态 | 范围 |
|---|---|---|
| **Phase 0** | ✅ 已完成 | 前后端基础骨架 + 联通自检 |
| Phase 1 | ⏳ 待开始 | 前端 UI (三栏布局 + 登录) |
| Phase 2 | ⏳ 待开始 | 后端业务接口（LLM/Agent/SSE） |
| Phase 3 | ⏳ 待开始 | 前后端联调（ECharts 真实可视化） |

## 📁 目录结构

```
111/
├─ backend/                       FastAPI + LangChain + SQLite
│  ├─ app/                        后端代码
│  ├─ data/                       SQLite 数据库
│  ├─ tests/                      单元测试
│  ├─ requirements.txt
│  ├─ run.py                      一键启动入口
│  └─ .env.example                配置模板
├─ frontend/                      React + Vite + AntD
│  ├─ src/                        前端代码
│  ├─ package.json
│  └─ vite.config.ts
├─ docs/                          设计文档
├─ start.bat                      Windows 一键启动
└─ README.md
```

## 🚀 Phase 0 启动方式

### 前置依赖

- Python 3.11+
- Node.js 18+
- npm / pnpm / yarn

### 1. 后端

```bash
cd backend

# (可选) 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# 安装依赖（Phase 0 仅核心 4 包，几秒完成）
pip install -r requirements.txt

# 启动
python run.py
```

后端运行在 **http://localhost:8000**
- `GET /api/health` 健康检查
- `GET /docs` Swagger 文档

### 2. 前端（新开终端）

```bash
cd frontend
npm install                    # 首次较慢
npm run dev
```

前端运行在 **http://localhost:5173**（Vite 已配 `/api/*` → 8000 代理）

### 3. 一键启动（Windows）

双击 `start.bat` 自动开两个窗口分别起前后端。

## ✅ Phase 0 验收清单

打开浏览器访问 http://localhost:5173：

- [x] AntD 中文界面渲染正常
- [x] 页面显示"前后端联通自检"
- [x] 卡片内显示 `{"status":"ok","version":"phase0",...}`
- [x] 重新检测按钮可刷新后端响应

## ⚙️ 环境变量

后端从 `backend/.env` 读取（从 `.env.example` 复制即可）：

| 变量 | 说明 |
|---|---|
| `DASHSCOPE_API_KEY` | 阿里云百炼 API Key（**Phase 2 启用，前端不需要填写**） |
| `APP_PORT` | 后端端口，默认 8000 |
| `CORS_ORIGINS` | 允许的前端来源，逗号分隔 |
| `QWEN_CHAT_MODEL` | 对话模型，默认 `qwen3-plus` |
| `QWEN_SQL_MODEL` | SQL 生成模型，默认 `qwen3-coder-plus` |
| `SQLITE_PATH` | SQLite 文件路径 |

## 🛣 路线图

- **Phase 1** · 前端：完整三栏（会话/问答/图表）+ 登录页 + Mock 数据
- **Phase 2** · 后端：LLM 接入、SQLite、Agent、SSE、安全层、会话存储
- **Phase 3** · 联调：ECharts 真实渲染、上下文记忆、E2E 完整闭环

## 📖 设计文档

完整架构与分阶段细节见 [docs/architecture.md](docs/architecture.md)。
