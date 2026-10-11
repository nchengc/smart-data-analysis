# 「智能数据分析系统」 — 系统模块规划

## 一、Context（背景与目标）

构建一个本地运行的 **自然语言 → 数据分析 → 智能可视化** 平台。核心落地需求：

| 编号 | 需求 | 本方案如何落 |
|---|---|---|
| 1 | 接入大模型 (Qwen3 + 阿里云百炼) | 通过 DashScope SDK（`langchain_community.chat_models.ChatTongyi`）调用阿里云百炼上的 `qwen3` / `qwen3-max` / `qwen3-coder` |
| 2 | 操作 SQLite、自然语言→SQL→执行 | LangChain `SQLDatabaseToolkit` + `create_sql_agent`，自带 schema 查询与 SQL 执行工具 |
| 3 | 前端实时可视化图表 | 大模型按约定的 `chart_suggestion` JSON 输出，前端用 ECharts 即时渲染 |
| 4 | **会话管理 + 上下文记忆** | 后端 `sessions` + `messages` 两张表持久化每轮问答，前端左侧栏展示会话列表，Agent 注入 `chat_history` 实现多轮追问理解 |
| 5 | **React 前端三栏布局** | `<Layout>` 左 Sider(会话管理) + 中间 Content(问答区域) + 右 Sider(可视化图表) |

**目标**：本地 `python run.py` + `npm run dev` 即用；不依赖 Docker / 云服务；阿里云百炼 API Key 通过 `.env` 注入。

---

## 二、技术栈最终落地清单

| 层 | 选型 | 关键依据 |
|---|---|---|
| **LLM 接入** | **阿里云百炼 + DashScope SDK** | 用户明确指定；用 `langchain_community.chat_models.ChatTongyi(model="qwen3-max", ...)` 即可一行接 LangChain 生态 |
| **主对话模型** | `qwen3-max` / `qwen3-plus`（路由）| Qwen3 系列指令遵循与 Function Calling 最稳的版本 |
| **SQL 生成特化** | `qwen3-coder` | 自带代码纠错，对 SQL 语法精度更高 |
| **Agent 框架** | **LangChain**（`create_sql_agent`） + LangGraph（按需升级 ReAct） | 用户明确 LangChain 主推 |
| **后端 Web** | FastAPI（异步、SSE、Pydantic 校验）| 用户明确指定 |
| **数据库** | SQLite（业务数据）+ SQLite（会话存储，**同一 DB 不同 schema**）| 用户明确指定 |
| **Schema 检索** | `<50 表`：全量 DDL 塞 system prompt；`>50 表`：Chroma 向量库（按需启用，本期先做轻量）| 控制复杂度 |
| **前端框架** | **React 18 + Vite + TypeScript** | 用户明确 React；Vite 启动最快；TS 对齐后端契约 |
| **UI 组件** | Ant Design 5（含 Layout / Menu / List / Card） | 内置三栏 Layout，企业级标配 |
| **可视化** | **Apache ECharts**（`echarts` + `echarts-for-react`）| 国内 BI 标配；LLM 输出 option JSON 直接渲染 |
| **前后端通信** | SSE（流式问答）+ REST（会话 CRUD） | 单向流式最适合 LLM 输出；WebSocket 过度 |
| **状态管理** | React `useState` + `useReducer`（轻量）| 不引入 Redux/Zustand，避免多余依赖 |
| **HTTP** | `fetch` + `EventSource` 浏览器原生 | 不引入 axios |
| **类型校验** | **Pydantic v2**（后端）+ TypeScript（前端）| 前后端契约强对齐 |

---

## 三、整体架构图

```
┌──────────────────────────────────────────────────────────┐
│  前端 React + Vite + AntD Layout                         │
│  ┌─LeftSider─┬────Content─────┬──RightSider──┐          │
│  │ Session   │  ChatPanel     │  ChartPanel  │          │
│  │ List      │  - 消息列表    │  - ECharts    │          │
│  │ + 新会话   │  - 输入框      │  - 表格       │          │
│  │ + 删除/重命名│ - 流式响应   │  - SQL 预览   │          │
│  └───────────┴────────────────┴──────────────┘          │
└──────────────────────────────────────────────────────────┘
                  │ SSE + REST
                  ▼
┌──────────────────────────────────────────────────────────┐
│  FastAPI 后端                                            │
│  ├─ /api/sessions        GET / POST / DELETE            │
│  ├─ /api/sessions/{id}   GET / PATCH (重命名)           │
│  ├─ /api/sessions/{id}/messages  GET (历史)              │
│  ├─ /api/chat            POST (SSE 流式, 携带 session_id)│
│  └─ /api/schema          GET (返回 DB schema 元数据)     │
└──────────────────────────────────────────────────────────┘
       │                                 │
       │ ConversationBufferMemory         │ SQLDatabaseToolkit
       ▼                                 ▼
┌──────────────────────┐    ┌──────────────────────────┐
│ LangChain Agent       │    │ SQLAlchemy 只读引擎         │
│ + ChatTongyi(qwen3)   │───▶│ SQLite (./data/app.db)    │
│ + ConversationMemory │    └──────────────────────────┘
└──────────────────────┘
```

---

## 四、系统模块拆解

### 模块 1️⃣ LLM 接入层（`backend/app/llm/`）

| 项 | 说明 |
|---|---|
| 文件 | `llm/client.py` |
| 责任 | 包装 `ChatTongyi` 实例，提供单例；按任务路由 `qwen3-max` / `qwen3-coder` |
| 关键配置 | `DASHSCOPE_API_KEY`、`QWEN_CHAT_MODEL`、`QWEN_SQL_MODEL`、`REQUEST_TIMEOUT` |
| 失败兜底 | API 限流/超时自动重试一次；返回原始错误给前端 |

```python
# backend/app/llm/client.py —— 示意
from langchain_community.chat_models import ChatTongyi

def get_llm(temperature=0.1, model: str | None = None) -> ChatTongyi:
    return ChatTongyi(
        model=model or settings.QWEN_CHAT_MODEL,
        api_key=settings.DASHSCOPE_API_KEY,
        temperature=temperature,
        timeout=settings.REQUEST_TIMEOUT,
        max_retries=1,
    )
```

### 模块 2️⃣ 数据库层（`backend/app/db/`）

| 子模块 | 文件 | 职责 |
|---|---|---|
| 业务 DB 引擎 | `db/engine.py` | SQLAlchemy 只读连接池（防止误写） |
| Schema 反射 | `db/metadata.py` | 用 `SQLDatabase.from_uri()` 拉所有 DDL + 样例值，供 Prompt 注入 |
| 会话存储 | `db/session_store.py` | 用 SQLite `sessions` + `messages` 两张表存会话与历史 |
| 初始化 | `db/init_db.py` | 启动时跑：建业务表 + 注入示例电商数据集 + 建 sessions/messages 两表 |
| 示例数据 | `data/seed.sql` | 包含 customers / orders / products / categories 四张表，~500 条 |

**会话表结构：**
```sql
CREATE TABLE sessions (
    id           TEXT PRIMARY KEY,        -- uuid4
    title        TEXT,                     -- 默认取首条问题前 20 字
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    db_snapshot  TEXT                      -- 冗余：会话对应的 DB 版本（未来支持多库）
);

CREATE TABLE messages (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id   TEXT NOT NULL,
    role         TEXT NOT NULL,            -- 'user' | 'assistant' | 'system'
    content      TEXT NOT NULL,            -- 用户原文 / 助手 JSON 字符串 / 系统提示
    chart_json   TEXT,                     -- 助手消息专属，可视化 JSON
    sql_text     TEXT,
    data_json    TEXT,                     -- 查询结果数据集
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);
CREATE INDEX idx_messages_session ON messages(session_id);
```

### 模块 3️⃣ 安全校验层（`backend/app/security/`）

| 文件 | 职责 |
|---|---|
| `security/sql_sanitizer.py` | sqlparse AST：仅允许 `SELECT`，禁 `INSERT/UPDATE/DELETE/DROP/ALTER/PRAGMA/ATTACH/load_extension`；自动 LIMIT 注入 |
| `security/errors.py` | 统一异常类型 |

### 模块 4️⃣ Agent 层（`backend/app/agents/`）—— 核心

| 文件 | 职责 |
|---|---|
| `agents/sql_agent.py` | `create_sql_agent(llm=ChatTongyi(qwen3-coder), db=SQLDatabase, agent_type="tool-calling", verbose=True)`；输出强制 JSON |
| `agents/memory.py` | **会话记忆**：从 DB 加载最近 N 条消息 → 转 LangChain `ConversationBufferMemory` / 装入 prompt |
| `agents/prompts.py` | SQLite 方言提示 + Few-shot 示例 + JSON Schema 约束 |
| `agents/runner.py` | 同步执行入口；处理 SQL 生成 → 校验 → 执行 → 反思（最多 2 轮）→ 总结 + 图表建议 |

**Agent 关键 prompt（精简版）：**
```
你是 SQLite 数据分析助手。可用表和列：
{schema}

用户问题：{question}

上一轮对话摘要：{chat_history}

要求：
1. 仅生成 SELECT，必要时用 strftime 处理日期（勿用 DATE_FORMAT）
2. 表/列名全小写下划线
3. 必须返回 JSON：{"sql":"...","chart":{"type":"bar|line|pie|scatter|table","x":"col","y":"col","title":"..."},"summary":"..."}
4. 无匹配数据时 chart.type="table"，summary 给出原因
```

**Reflection 触发条件（自动纠错）：**
- sqlparse 校验失败 → 携带错误回喂 LLM 改写
- SQL 执行异常（`OperationalError`） → 回喂报错信息改写
- 最多 2 轮，超出则把错误回给用户并提示简化问题

### 模块 5️⃣ 会话管理 + 上下文记忆（`backend/app/api/sessions.py`）—— **用户重点需求**

| 接口 | 方法 | 功能 |
|---|---|---|
| `/api/sessions` | `GET` | 列出会话（按 `updated_at desc`） |
| `/api/sessions` | `POST` | 创建空会话 |
| `/api/sessions/{id}` | `PATCH` | 重命名 |
| `/api/sessions/{id}` | `DELETE` | 软删 / 硬删 |
| `/api/sessions/{id}/messages` | `GET` | 拉历史消息 |
| `/api/chat` | `POST` | **核心**：传 `{session_id, question}`，SSE 流式回答；Agent 内部注入该会话前 N 条消息作为上下文 |

**记忆策略**（简单可控）：
1. 加载该 session 最近 5 对 messages（≈10 条）
2. 若总 token > 3000，**降级为摘要**：调 LLM 摘要后存 `sessions.context_summary`，下次拼接
3. SQL 执行结果保留原 data_sample 写入 `messages.data_json`，便于前端直接复用

### 模块 6️⃣ 可视化协议层

**LLM 输出的标准 JSON 契约**（`backend/app/schemas/chat.py` 与 `frontend/src/types/api.ts` 一致）：

```typescript
export interface ChartSpec {
  type: 'bar' | 'line' | 'pie' | 'scatter' | 'table';
  x?: string;
  y?: string | string[];
  group_by?: string;
  agg?: 'sum' | 'avg' | 'count' | 'max' | 'min';
  title?: string;
  extra?: Record<string, unknown>;
}

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  sql?: string;
  chart?: ChartSpec;
  data?: Record<string, unknown>[];
  row_count?: number;
}

export interface Session {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}
```

前端 `echartsAdapter(chart_spec, data)` 函数（`frontend/src/lib/chartAdapter.ts`）做映射：

| `chart.type` | ECharts `option` 模板 |
|---|---|
| `bar` | `xAxis = chart.x`, `series = [{type:'bar', data: data.map(d=>d[y])}]` |
| `line` | 同上 + `smooth: true` |
| `pie` | `series = [{type:'pie', data: data.map(d=>({name:d[x],value:d[y]}))}]` |
| `scatter` | `xAxis.valueAxis` + 二维点 |
| `table` | 退化为 Antd `<Table>` 组件 |

---

## 五、前端三栏布局设计

### 5.1 布局（AntD `Layout`）

```
┌─────────────────────────────────────────────────────────────┐
│  Header  (Logo  · 标题 · 当前会话名 · 设置)  [48px 高]        │
├──────────┬────────────────────────────────┬──────────────────┤
│          │                                │                  │
│  Left    │          Center                │    Right         │
│  Sider   │      ChatPanel                │   ChartPanel     │
│ (260px)  │      消息流 + 输入框           │   (380px)        │
│          │                                │                  │
│ 会话列表  │  ┌─ 助手消息 ────────────┐    │  ECharts / Table │
│ ─────    │  │ 用户问：...             │    │  SQL 预览        │
│ + 新会话  │  │                       │    │  数据表格        │
│ ▸ 会话1   │  │ 助手答：summary        │    │                  │
│ ▸ 会话2   │  │  + 嵌入小图表           │    │  当无数据时：     │
│ ▸ 会话3   │  └─────────────────────┘    │   "先提问试试"     │
│          │                                │                  │
│          │  [输入框 ___________________]│                  │
│          │  [ 发送 (Enter 发送)        ] │                  │
│          │                                │                  │
└──────────┴────────────────────────────────┴──────────────────┘
```

### 5.2 关键组件（`frontend/src/components/`）

| 组件 | 职责 | 关键 props |
|---|---|---|
| `AppLayout.tsx` | AntD Layout 三栏骨架 | — |
| `SessionSidebar.tsx` | 左侧：会话列表 + 新建/重命名/删除 | `onSelect` |
| `ChatPanel.tsx` | 中间：消息流 + 输入框，SSE 订阅 | `sessionId` |
| `MessageItem.tsx` | 单条消息；助手消息内嵌 mini 图表 | `message` |
| `ChartPanel.tsx` | 右侧：根据最后一条助手消息渲染 | `chart?, data?, sql?` |
| `EChartsView.tsx` | ECharts 通用包装 | `option` |
| `DataTable.tsx` | Antd Table 展示 data_sample | `columns, dataSource` |
| `SqlPreview.tsx` | 高亮显示 SQL（用 `react-syntax-highlighter`） | `sql` |

### 5.3 状态管理（不引入额外库）

```
App
 ├─ activeSessionId   (useState)
 ├─ sessions[]        (useState, 启动时 fetch)
 ├─ messagesBySession (useState<Record<sessionId, ChatMessage[]>>)
 └─ lastChartData     (useState, 中间收到时推到右侧)
```

切换 session 时按需加载 messages；问新问题时清空 lastChartData。

### 5.4 SSE 流式消费（`frontend/src/hooks/useChatStream.ts`）

- 使用 `fetch` + `ReadableStream`（兼容性比 `EventSource POST` 好）；
- 模型流式输出：`event: token` → 拼接到当前助手消息的 `content`；
- 最终输出：`event: done` → 携带完整 `chart + data + sql` JSON；
- 中间过程可以发：`event: sql` / `event: chart_suggestion` 等事件，让中间面板先动起来。

---

## 六、SQLite 适配要点

| 限制 | 影响 | 解决方案 |
|---|---|---|
| 不支持 `RIGHT JOIN` / `FULL JOIN` | 模型可能写出标准 JOIN | Prompt 显式提示，避免 |
| 无 `DATE_FORMAT()` | 模型习惯 MySQL 语法 | Prompt 提示 "用 `strftime('%Y-%m', x)`" |
| 无 `BOOLEAN`，存 0/1 | 前端图表判定 | `chartAdapter` 自动将 `0/1` 渲染为 `false/true` |
| 表/列名默认大小写敏感 | 跨方言迁移易错 | Prompt 约定 "全小写 + 下划线" |
| 无 `ILIKE` | 大小写不敏感匹配 | `LIKE 'x%' COLLATE NOCASE` |
| 并发写锁 | 多用户同写阻塞 | **系统只读**：写权限完全不授予连接 |

---

## 七、目录结构（最终）

> **项目根目录**：`G:\【0】209 Python\智能问数据平台\111\`（所有代码、依赖、运行产物都放在此目录下，保持 `智能问数据平台/` 父目录干净）

```
G:\【0】209 Python\智能问数据平台\111\       ← 项目根（所有内容在此目录下生成）
├─ backend\
│  ├─ app\
│  │  ├─ main.py                  # FastAPI 入口、路由挂载
│  │  ├─ config.py                # Pydantic Settings，读取 .env
│  │  ├─ llm\client.py            # ChatTongyi 单例
│  │  ├─ db\
│  │  │  ├─ engine.py             # 业务 DB SQLAlchemy 只读引擎
│  │  │  ├─ metadata.py           # 反射 schema
│  │  │  ├─ session_store.py      # 会话/消息 SQLite 存储
│  │  │  └─ init_db.py            # 启动时建库+示例数据
│  │  ├─ security\
│  │  │  ├─ sql_sanitizer.py      # sqlparse 白名单
│  │  │  └─ errors.py
│  │  ├─ agents\
│  │  │  ├─ sql_agent.py          # LangChain create_sql_agent
│  │  │  ├─ memory.py             # 会话摘要 + 切片注入
│  │  │  ├─ prompts.py            # Prompt 模板
│  │  │  └─ runner.py             # 单轮执行入口（含 Reflection）
│  │  ├─ schemas\                 # Pydantic 模型
│  │  │  ├─ chat.py
│  │  │  ├─ session.py
│  │  │  └─ chart.py
│  │  └─ api\
│  │     ├─ chat.py               # /api/chat (SSE)
│  │     ├─ sessions.py           # 会话 CRUD
│  │     └─ schema.py             # /api/schema
│  ├─ data\
│  │  ├─ app.db                   # 业务+会话（SQLite 单文件）
│  │  └─ seed.sql                 # 初始化 DDL + 示例数据
│  ├─ tests\
│  │  └─ test_sql_sanitizer.py
│  ├─ requirements.txt
│  └─ .env.example                # DASHSCOPE_API_KEY=xxx
├─ frontend\
│  ├─ src\
│  │  ├─ App.tsx
│  │  ├─ main.tsx
│  │  ├─ components\             # 见 5.2
│  │  ├─ hooks\useChatStream.ts
│  │  ├─ lib\chartAdapter.ts
│  │  ├─ lib\api.ts               # fetch 封装
│  │  └─ types\api.ts             # 与后端 Pydantic 对齐
│  ├─ index.html
│  ├─ vite.config.ts
│  ├─ package.json
│  └─ tsconfig.json
├─ docs\
│  └─ architecture.md             # 实施明细
├─ .gitignore
├─ README.md                      # 一键启动 + 使用说明
├─ run.py                         # 一键启动脚本（uvicorn）
└─ start.bat                      # Windows 启动器（双击即起前后端）
```

**绝对路径速查**（开发时常用）：
- 后端根：`G:\【0】209 Python\智能问数据平台\111\backend`
- 前端根：`G:\【0】209 Python\智能问数据平台\111\frontend`
- 数据库文件：`G:\【0】209 Python\智能问数据平台\111\backend\data\app.db`
- 环境变量：`G:\【0】209 Python\智能问数据平台\111\backend\.env`（从 `.env.example` 复制）
- 一键启动：双击 `G:\【0】209 Python\智能问数据平台\111\start.bat`

---

## 七B、严禁事项

为了保持 `G:\【0】209 Python\智能问数据平台\` 父目录整洁：
- ❌ **不要**直接在父目录（`智能问数据平台/`）下生成任何代码、`package.json`、`requirements.txt`、日志、缓存
- ❌ **不要**用相对路径回退到父目录
- ✅ 所有生成文件、命令执行的 cwd、Python 的脚本路径都必须在 `111\` 子目录下
- ✅ VSCode 在打开项目时，应打开 `111\` 作为工作区根（不是父目录）

---

## 八、关键依赖清单

**后端** (`backend/requirements.txt`)：
```
fastapi>=0.115
uvicorn[standard]>=0.32
pydantic>=2.10
pydantic-settings>=2.6
sqlalchemy>=2.0
sqlparse>=0.5
langchain>=0.3
langchain-community>=0.3         # 内含 ChatTongyi(DashScope SDK 已被官方迁移至此)
dashscope>=1.20                  # 官方 DashScope SDK（ChatTongyi 底层依赖）
python-dotenv>=1.0
sse-starlette>=2.0
```
> `qwen3` 模型：百炼平台 model 名用 `qwen3-max` / `qwen3-plus` / `qwen3-coder-plus`（具体以百炼控制台为准）。

**前端** (`frontend/package.json` 核心)：
```
react ^18, react-dom ^18
vite ^6, @vitejs/plugin-react ^4
typescript ^5, @types/react ^18
antd ^5, @ant-design/icons ^5
echarts ^5, echarts-for-react ^3
react-markdown ^9                # 富文本显示助手回答
react-syntax-highlighter ^15     # SQL 高亮
```

---

## 九、分 4 阶段实施计划（用户最新指示）

> 把整个交付拆为 **phase 0 → 1 → 2 → 3**，**前一阶段验收通过才进入下一阶段**。每个 phase 结束都给出"可运行验证清单"。

### Phase 0 — 前后端基础框架（让骨架跑起来）

**目标**：前后端项目各能独立启动，并能通过 HTTP 联通验证。

| 子任务 | 关键产出文件 | 验收 |
|---|---|---|
| 0.1 后端骨架 | `backend/app/main.py`（FastAPI ping 接口 `GET /api/health` + CORS 配通）<br>`backend/requirements.txt`<br>`backend/.env.example` | `curl http://localhost:8000/api/health` → `{"status":"ok"}` |
| 0.2 后端依赖安装 | `pip install -r requirements.txt` | `python -c "import fastapi, langchain, dashscope"` 不报错 |
| 0.3 后端启动脚本 | `backend/run.py`（uvicorn 包装，host=0.0.0.0, port=8000, reload=True） | `python run.py` 一行启动 |
| 0.4 前端骨架 | `frontend/package.json` + `vite.config.ts` + `tsconfig.json`<br>`frontend/index.html`<br>`frontend/src/main.tsx` + `App.tsx`（AntD ConfigProvider + 一个占位按钮 + 中文 Locale） | `npm run dev` → 浏览器自动打开 React + AntD 页面，按钮有样式 |
| 0.5 前端代理 | `frontend/vite.config.ts` 中 `server.proxy['/api']` 指向 `http://localhost:8000` | 前端 fetch `/api/health` 不报 CORS |
| 0.6 根目录启动器 | `start.bat` / `start.sh` 同时起后端和前端（两个后台窗口） | 双击 start.bat → 两个服务都跑起来 |
| 0.7 一份 README | `README.md`：介绍目录结构、启动方式、当前是 phase 0 | 另一个人能上手 |

**Phase 0 测试清单（交付前自检）**：
```bash
# 终端1
cd backend && pip install -r requirements.txt && python run.py
# 终端2
curl http://localhost:8000/api/health   # 期望 {"status":"ok","version":"phase0"}

# 终端3
cd frontend && npm install && npm run dev
# 浏览器打开 http://localhost:5173 → 看到 AntD 按钮 + 后端返回的 "FastAPI ok" 字符串
```

### Phase 1 — 前端 UI 开发 + 用户登录

**目标**：完整的前端三栏布局 + 登录页面 + 不依赖后端的 mock 数据流转，方便用户"登录测试"和验收交互。

| 子任务 | 关键产出 | 验收 |
|---|---|---|
| 1.1 AntD 三栏骨架 | `AppLayout.tsx`：Header 48px + LeftSider 260px + Content + RightSider 380px | 浏览器三栏正常显示 |
| 1.2 登录页 | `pages/Login.tsx`：居中卡片 + 用户名密码 + "登录"按钮（**前端 mock**：账号 `demo` / 密码 `demo` 即视为登录成功） | 输入 demo/demo → 跳到工作台 |
| 1.3 路由 | 引入 `react-router-dom`，未登录跳 Login、登录后跳 Workspace | F5 刷新仍保持登录态（localStorage） |
| 1.4 工作台左 Sider | `SessionSidebar.tsx`：AntD `Menu` + 新建会话按钮 + 会话列表（**mock 数据，3 条假会话**） | 新建/删除/重命名会话能用 |
| 1.5 工作台中间 Content | `ChatPanel.tsx`：消息流 + 输入框；mock 时本地用 `useState` 维护假对话（用户问 → 1 秒后假回答"这是 mock 回答"） | 能输入问题、看到假回答 |
| 1.6 工作台右 Sider | `ChartPanel.tsx`：占位 + "暂无数据"提示；mock 时点击"假图表"按钮渲染一张本地假 ECharts 图（数据写死） | 右侧能看到一张静态图 |
| 1.7 登录测试 | 完整 demo：登录 → 工作台 → 新建会话 → 输入"查询销售总额" → 右侧显示 mock 图 | 用户能完整跑通 demo 流程 |

**Phase 1 测试清单（必须全过）**：
- [ ] 访问 `http://localhost:5173/login` 看到登录卡片
- [ ] demo/demo 登录成功，跳到工作台
- [ ] 错误账号密码被前端拦截
- [ ] 工作台三栏显示正常，移动光标 hover 各会话有 hover 高亮
- [ ] 新建会话：列表出现新会话并自动选中
- [ ] 输入"销售总额"，1 秒后中间显示 mock 回答、右侧显示一张柱状图
- [ ] 切换会话能切换 mock 消息

> ⚠️ **登录澄清**：用户提到"登录测试"。本 phase 把登录定为**前端 demo 登录**（不接数据库账号表，账号硬编码为 `demo/demo`，通过即视为登录）。后续如有真实认证需求再升级。

### Phase 2 — 后端接口开发

**目标**：所有后端接口真实实现（不再 mock），并提供 `curl`/Swagger 文档可调试。

| 子任务 | 关键产出 | 验收 |
|---|---|---|
| 2.1 配置层 | `app/config.py`（Pydantic Settings 读 .env）<br>`app/llm/client.py`（ChatTongyi 单例 + 路由：简单 qwen3-plus / SQL qwen3-coder-plus） | `.env` 注入 key 后能 `get_llm().invoke("hi")` |
| 2.2 数据库层 | `app/db/engine.py`（SQLAlchemy 只读引擎）<br>`app/db/init_db.py` + `data/seed.sql`（4 表 + 500 行样本：customers/orders/products/categories） | 启动后 `app.db` 存在，能 `sqlite3 app.db ".tables"` 看到表 |
| 2.3 Session 存储 | `app/db/session_store.py`（封装 sessions/messages CRUD） | 直接调用 `store.create()` 成功 |
| 2.4 Schema 元数据 | `app/db/metadata.py`（LangChain `SQLDatabase.from_uri` 反射 DDL + sample） | `db.get_table_info()` 返回所有 DDL |
| 2.5 SQL 安全层 | `app/security/sql_sanitizer.py`（sqlparse 白名单 + LIMIT 注入）<br>`tests/test_sql_sanitizer.py`（5 个用例） | `pytest tests/` 全绿，恶意 `DROP TABLE` 被拦截 |
| 2.6 Agent 核心 | `app/agents/prompts.py`<br>`app/agents/memory.py`（按 session 拉历史 + 摘要降级）<br>`app/agents/sql_agent.py`（create_sql_agent，含 Reflection 2 轮）<br>`app/agents/runner.py`（统一入口） | `runner.run(question, session_id=...)` 返回 `{sql, chart, summary, data, row_count}` |
| 2.7 API 接口 | `app/api/sessions.py`：5 个 session 接口<br>`app/api/schema.py`：`GET /api/schema`<br>`app/api/chat.py`：`POST /api/chat`（SSE 流式） | Swagger `/docs` 看到所有接口；`/api/schema` 返回 DDL JSON |
| 2.8 接口联调自测 | 用 curl 走完：创建会话 → 提问 → 收 SSE 流 → 数据库查 messages 验证入库 | 全部接口正常 |

**Phase 2 测试清单（必须全过）**：
- [ ] `GET /api/schema` 返回字符串包含 `CREATE TABLE orders`
- [ ] `POST /api/sessions` 返回 `{"id":"uuid"}`
- [ ] `POST /api/chat` 流式收到 `event: token` 与 `event: done`
- [ ] `python -c "from app.agents.runner import run; print(run('...', session_id='x'))"` 返回含 `sql`/`chart`/`summary`
- [ ] `pytest backend/tests/` 全绿
- [ ] 注入一句包含 `' OR 1=1` 的 SQL，安全层直接拒绝

### Phase 3 — 前后端联调

**目标**：把前端 mock 数据全部替换为真实后端调用，完整 E2E 跑通。

| 子任务 | 关键产出 | 验收 |
|---|---|---|
| 3.1 前端 API 层 | `lib/api.ts`：封装 `fetch` 调用 REST 接口 + `useChatStream` Hook 实现 SSE | `api.listSessions()` 拿到真实数据 |
| 3.2 替换会话管理 | `SessionSidebar.tsx` 改用 `api.listSessions / createSession / renameSession / deleteSession` | 刷新后仍能看到会话 |
| 3.3 替换聊天 | `ChatPanel.tsx` 改用 `useChatStream`，流式 token 实时拼接、SQL 完成后显示 | 输入问题，文本一个字一个字出来 |
| 3.4 替换图表渲染 | `ChartPanel.tsx` + `lib/chartAdapter.ts` 接后端 `chart` JSON → ECharts option | 图表随回答刷新 |
| 3.5 类型对齐 | `types/api.ts` 与 `schemas/*.py` 严格匹配 | TS 编译不报错 |
| 3.6 上下文记忆验证 | 同一会话连续追问"再过滤掉 X" / "换成 X 图"——Agent 注入历史能延续 | 多轮问答连贯 |
| 3.7 E2E 回归 | 完整流程：登录 → 新建会话 → 提问 → 流式回答 → 图表渲染 → 切换会话 → 删除会话 | 全程无报错 |

**Phase 3 测试清单（必须全过）**：
- [ ] `npm run dev` + `python run.py`，浏览器能完整操作
- [ ] F12 网络面板看到 SSE 流事件
- [ ] 单测、E2E 都过；DLQ（前端调试日志）无红色错误
- [ ] 重启后端后历史会话与消息仍在（持久化）
- [ ] README 完善到"另一个人不报错能直接跑通"

---

### Phase 间切换门禁（Review Checkpoint）

每个 phase 结束、进入下个 phase 前，都要逐条核对上面的"测试清单"——**全部 ✅ 才能进下个 phase**。如果任何一项 ❌，**就地修复，绝不拖着问题进入下一 phase**（避免后期 debug 难以定位是 frontend 还是 backend 的问题）。

---

## 十、安全 / 可扩展 备忘

- **SQL 注入**：白名单 + sqlparse AST + 参数化绑定（即使模型输出 `'; DROP TABLE --`，白名单也直接拦截）
- **API Key 隔离**：仅放 `.env`；`.gitignore` 排除；前端代码绝不出现明文
- **可观测性**：每个 SSE 事件带 `elapsed_ms`；错误堆栈保留最近一条
- **后续可扩展方向**：
  - 多数据源抽象（PostgreSQL/MySQL）
  - 图表对话式编辑（"换成折线图"→ 仅改 chart.type 重渲染）
  - LangSmith / LangFuse 全链路 trace
  - 用户登录与多租户隔离

---

## 十一、与上版plan的差异说明

| 项 | 上版 | 本版（根据用户细化需求） |
|---|---|---|
| LLM 接入 | DashScope SDK（未指定百炼） | **明确为阿里云百炼 + Qwen3**，用 `ChatTongyi` |
| Agent 主推 | LangGraph | **LangChain**（`create_sql_agent`）；LangGraph 降级为进阶 |
| 会话管理 | 未涉及 | **新增模块**：`sessions`/`messages` SQLite + API |
| 上下文记忆 | 未涉及 | **新增模块**：History 摘要 + ConversationBufferMemory 注入 |
| 前端布局 | 整体 Workspace | **明确三栏**：左 Sider / 中 Content / 右 Sider |
| UI 库 | Ant Design | Ant Design **必须**（自带 Layout 三栏） |
| 目标交付 | 选 3 套其一 | **唯一推荐栈**：FastAPI + LangChain + AntD + ECharts + SSE |

