# 智能数据分析系统

> **自然语言提问 → 自动数据分析 → 智能可视化呈现**
>
> Qwen3 + LangChain + FastAPI + React 18 + Ant Design + ECharts

## 🎉 4 Phase 全部完成

| Phase | 内容 | 状态 |
|---|---|---|
| **0** | 前后端基础骨架（FastAPI + Vite + CORS + Proxy） | ✅ |
| **1** | 前端 UI：三栏布局 + 登录 + Mock 数据 | ✅ |
| **2** | 后端业务：LangChain SQL Agent + SQLite + Qwen3 + SSE | ✅ |
| **3** | 前后端联调 E2E：SSE 流式 + 智能 ECharts + 持久化 | ✅ |

**GitHub**: https://github.com/nchengc/smart-data-analysis

---

## 📦 项目结构

```
111/
├─ backend/                 FastAPI + LangChain + SQLite + Qwen3
│  ├─ app/
│  │  ├─ main.py            FastAPI 入口
│  │  ├─ config.py          Pydantic Settings
│  │  ├─ llm/client.py      ChatTongyi 单例
│  │  ├─ db/
│  │  │  ├─ engine.py       SQLAlchemy 只读引擎
│  │  │  ├─ init_db.py      启动自动建表
│  │  │  ├─ seed_data.py    ~600 行示例数据
│  │  │  ├─ session_store.py
│  │  │  └─ metadata.py     LangChain SQLDatabase 反射
│  │  ├─ security/
│  │  │  ├─ sql_sanitizer.py sqlparse 白名单
│  │  │  └─ errors.py
│  │  ├─ agents/
│  │  │  ├─ sql_agent.py    LangChain SQL Agent
│  │  │  ├─ runner.py       主入口（Reflection 2 轮 + JSON 总结）
│  │  │  ├─ memory.py       多轮上下文
│  │  │  └─ prompts.py
│  │  ├─ schemas/__init__.py Pydantic 契约
│  │  └─ api/
│  │     ├─ sessions.py     会话 CRUD（5 个）
│  │     ├─ schema.py       schema 反射
│  │     └─ chat.py         SSE 流式
│  ├─ data/
│  │  ├─ seed.sql           DDL
│  │  └─ app.db             业务 + 会话（自动 init）
│  ├─ tests/                单元测试（20 用例）
│  └─ run.py
├─ frontend/                React 18 + Vite + AntD + ECharts
│  └─ src/
│     ├─ pages/
│     │  ├─ Login.tsx
│     │  └─ Workspace.tsx
│     ├─ components/        SessionSidebar / ChatPanel / ChartPanel / MessageItem / EChartsView
│     ├─ hooks/             useChatStream（SSE 订阅）
│     ├─ lib/               api.ts / chartAdapter.ts / mockData.ts / mockChat.ts
│     └─ types/             api.ts
├─ docs/                    设计文档
├─ start.bat                Windows 双击即起
├─ .gitignore
├─ .env.example             DASHSCOPE_API_KEY 配置模板
├─ README.md
└─ requirements.txt
```

---

## 🚀 快速启动

### 前置依赖
- Python 3.11+
- Node.js 18+
- （可选）阿里云百炼 API Key：[https://bailian.console.aliyun.com/](https://bailian.console.aliyun.com/)

### 1. 启动后端

```bash
cd backend
pip install -r requirements.txt

# 复制环境变量模板
copy .env.example .env
# 编辑 .env 填入 DASHSCOPE_API_KEY（无 key 也可启动，会走 fallback 路径）

# 启动（uvicorn，监听 :8000）
python run.py
```

启动后会自动：
- 初始化 SQLite（6 张表，~600 行示例数据）
- 在 `http://localhost:8000/docs` 显示 Swagger

### 2. 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端运行在 `http://localhost:5173`（已配置 `/api/*` 代理到 :8000）

### 3. 一键启动（Windows）

双击 `start.bat` 自动开两个窗口。

---

## 🧪 验收与使用

打开 `http://localhost:5173`：

- 登录页 → 账号 `demo` / 密码 `demo`
- 进入工作台三栏：
  - **左**：会话列表（持久化到 SQLite）
  - **中**：问答区域（SSE 流式输出）
  - **右**：智能 ECharts（自动选图：bar/line/pie/scatter）

### 测试用例

| 输入 | 预期 |
|---|---|
| 上月华东区销售额 | 数字 + 柱状图 |
| 各品类销量 | 横向柱状图 |
| 月度趋势 | 折线图（自动识别时间列）|
| 客户等级分布 | 饼图（≤6 行） |
| 销量 vs 客单价 | 散点图（2 数值列） |

---

## 🏗️ 架构关键点

### 后端（Phase 2）
- **LangChain SQL Agent** + `SQLDatabaseToolkit` 自然语言→SQL
- **Reflection 自纠错**（最多 2 轮）：SQL 执行报错回喂 LLM 改写
- **sqlparse 白名单**：仅允许 `SELECT`，禁 DDL/DML/`load_extension`/`PRAGMA`；强制 `LIMIT 1000`
- **SQLAlchemy 只读引擎**：`PRAGMA query_only=ON` 物理级只读
- **会话持久化**：SQLite `sessions` + `messages` 表，与业务表共存
- **JSON Schema 输出**：模型按约定 `summary + chart + sql + data` 返结构化结果

### 前端（Phase 3）
- **SSE 流式**：`fetch + ReadableStream` 解析 `event:` + `data:` 帧
- **智能 ECharts 适配器**：根据列名（时间关键词）+ 列类型 + 行数自动选 bar/line/pie/scatter
- **多轮对话**：每轮 `chat_history` 注入 Agent 上下文
- **本地 fallback**：当 LLM 不可用时走 mock 路径，保证流程完整

### 端到端
```
用户输入
   ↓
Workspace.handleAsk
   ↓ POST /api/chat/stream
useChatStream.start
   ↓
run_chat（后端）
   ↓ Agent → Reflection
   ↓ SQL 执行 + 图表推断
   ↓ SSE: phase / sql / data / chart / summary / done
   ↓
useChatStream.onDone
   ↓
ChatPanel 更新助手消息
   ↓
ChartPanel 同步渲染
   ↓
session_store 持久化
```

---

## 🔌 API 速查

| 方法 | 路径 | 用途 |
|---|---|---|
| GET  | `/api/health` | 健康检查 |
| GET  | `/api/sessions` | 列出会话 |
| POST | `/api/sessions` | 新建会话 |
| GET  | `/api/sessions/{id}` | 会话详情 |
| PATCH | `/api/sessions/{id}` | 重命名 |
| DELETE | `/api/sessions/{id}` | 删除 |
| GET  | `/api/sessions/{id}/messages` | 历史消息 |
| GET  | `/api/schema` | 返回 schema 文本 + 行数 |
| POST | `/api/chat/stream` | **SSE 流式问答** |

Swagger: `http://localhost:8000/docs`

---

## 🧪 测试

```bash
cd backend
python -m pytest tests/ -v
```

20 个 SQL 安全层单测（白名单/危险关键字/LIMIT/normalize）。

---

## ⚙️ 配置项（`backend/.env`）

| 变量 | 默认 | 说明 |
|---|---|---|
| `DASHSCOPE_API_KEY` | 空 | **必填**（无 key 走 fallback） |
| `QWEN_CHAT_MODEL` | `qwen3-plus` | 主对话模型 |
| `QWEN_SQL_MODEL` | `qwen3-coder-plus` | SQL 生成特化 |
| `REQUEST_TIMEOUT` | `120` | LLM 超时秒数 |
| `SQLITE_PATH` | `./data/app.db` | SQLite 文件路径 |
| `CORS_ORIGINS` | `http://localhost:5173` | 允许的前端来源 |
| `APP_PORT` | `8000` | 后端端口 |

---

## 🛣️ 已实现的能力

- ✅ 自然语言问 SQLite
- ✅ 自动 SQL 生成 + 安全校验 + 执行
- ✅ Reflection 自纠错
- ✅ 会话持久化（重启后历史仍在）
- ✅ 多轮对话上下文
- ✅ SSE 流式输出
- ✅ 智能 ECharts（自动选图）
- ✅ CORS / Proxy / 一键启动
- ✅ 20 个单元测试全绿

## 🚧 后续可选优化

- 多数据源（PostgreSQL / MySQL / DuckDB）
- 图表对话式编辑（"换成折线图"）
- LangSmith / LangFuse 全链路 trace
- 用户登录 + 多租户隔离
- 离线 Ollama 兜底
- Chroma 大表库 schema 检索

---

## 📄 License

MIT
