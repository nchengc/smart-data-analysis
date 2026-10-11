"""单轮 Agent 执行入口：传入问题 + session_id，返回统一结构。

设计：
1. 加载历史会话上下文
2. 调用 build_sql_agent.run() 跑 LangChain Agent
3. 用 sqlparse 白名单二次清洗生成的 SQL
4. 在 SQLite 上执行查询并拿结果
5. 如遇错误，调用 LLM 改写（最多 max_reflect 轮）
6. 最后调用总结 LLM 生成自然语言 summary + chart_suggestion
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.memory import build_history_text
from app.agents.prompts import REFLECT_SYSTEM, SQL_GEN_SYSTEM, SUMMARY_SYSTEM
from app.agents.sql_agent import build_sql_agent
from app.db.engine import get_engine
from app.db.metadata import get_schema_text
from app.db import session_store
from app.llm.client import get_chat_llm
from app.security.errors import AgentError, ReflectLimitExceeded
from app.security.sql_sanitizer import (
    SQLSecurityError,
    ensure_limit,
    normalize_sql,
    validate_select_only,
)


@dataclass
class ChatRunResult:
    session_id: str
    question: str
    sql: str
    chart: dict[str, Any]
    summary: str
    data: list[dict[str, Any]] = field(default_factory=list)
    row_count: int = 0
    reflection_rounds: int = 0
    elapsed_ms: int = 0
    error: str | None = None


def _exec_sql(sql: str, max_rows: int = 1000) -> tuple[list[dict[str, Any]], int]:
    """同步执行 SQL 返回 [(dict,)] 列表和总行数。"""
    eng = get_engine()
    with eng.connect() as conn:
        result = conn.exec_driver_sql(sql)
        columns = list(result.keys())
        rows = result.fetchmany(max_rows)
        # 总行数（粗略）
        total = len(rows)
        out = [dict(zip(columns, r)) for r in rows]
    return out, total


def _first_user_message(session_id: str) -> str:
    msgs = session_store.list_messages(session_id, limit=200)
    for m in msgs:
        if m["role"] == "user":
            return m["content"]
    return ""


def run_chat(session_id: str, question: str, *, max_reflect: int = 2) -> ChatRunResult:
    """主入口：传入 session_id + 问题，返回结果。

    会同时把 user/assistant 消息持久化到 session_store。
    """
    started = time.time()
    history_text = build_history_text(session_store.list_messages(session_id, limit=20))
    schema = get_schema_text()

    # 新会话自动标题
    if not session_store.get_session(session_id):
        raise AgentError(f"会话不存在：{session_id}")
    sess = session_store.get_session(session_id)
    if sess and sess.title == "新会话" or not sess.title:
        session_store.rename_session(session_id, session_store.auto_title_from_question(question))

    # 持久化用户消息
    session_store.append_message(session_id, "user", question)
    session_store.touch_session(session_id)

    chart: dict[str, Any] = {"type": "table", "title": ""}
    sql = ""
    summary = ""
    data: list[dict[str, Any]] = []
    row_count = 0
    error: str | None = None
    reflect_round = 0

    # 1) 用 SQL Agent 生成 SQL
    try:
        agent = build_sql_agent()
        prompt = SQL_GEN_SYSTEM.format(schema=schema) + (
            f"\n\n对话上下文：\n{history_text}\n\n用户问题：{question}\n"
            if history_text
            else f"\n\n用户问题：{question}\n"
        )
        agent_out = agent.invoke({"input": prompt})
        raw = (agent_out.get("output") or "").strip()
    except Exception as e:
        raw = ""
        error = f"agent 调用失败：{e}"

    # 2) 解析 LLM 输出拿 SQL
    sql = _extract_sql_from_agent_text(raw)
    summary_raw = raw

    # 3) 校验 + 执行（带 Reflection）
    while True:
        try:
            sql = normalize_sql(sql)
            validate_select_only(sql)
            sql = ensure_limit(sql, default_limit=1000)
            data, row_count = _exec_sql(sql)
            break
        except SQLSecurityError as e:
            error = f"SQL 安全拒绝：{e}"
            sql = "SELECT 'security_blocked' AS x;"
            data = [{"x": "blocked"}]
            row_count = 1
            break
        except Exception as e:
            # 真实执行错误：进入 reflection
            reflect_round += 1
            if reflect_round > max_reflect:
                error = f"Reflection 失败（{max_reflect} 轮）：{e}"
                sql = "SELECT 'error' AS x;"
                data = [{"x": "error"}]
                row_count = 1
                break
            # 让 LLM 改写
            sql = _reflect_sql(question, sql, str(e), schema) or sql
            # 回到顶端

    # 4) 调用 LLM 总结 + 选图表
    chart, summary = _summarize_and_chart(question, sql, data, summary_raw)

    # 5) 持久化助手消息
    session_store.append_message(
        session_id,
        "assistant",
        summary,
        chart=chart,
        sql=sql,
        data=data,
    )

    elapsed_ms = int((time.time() - started) * 1000)
    return ChatRunResult(
        session_id=session_id,
        question=question,
        sql=sql,
        chart=chart,
        summary=summary,
        data=data,
        row_count=row_count,
        reflection_rounds=reflect_round,
        elapsed_ms=elapsed_ms,
        error=error,
    )


def _extract_sql_from_agent_text(raw: str) -> str:
    """从 Agent 输出里抽出 SQL。"""
    if not raw:
        return "SELECT 'no_sql' AS x;"
    # 优先匹配 markdown ```sql 块
    m = re.search(r"```(?:sql)?\s*([\s\S]+?)```", raw, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    # 再尝试 "SQLQuery:" 之后的段
    m = re.search(r"SQLQuery\s*:\s*([\s\S]+)", raw, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    # 否则用整段
    return raw.strip()


def _reflect_sql(question: str, prev_sql: str, err: str, schema: str) -> str:
    """让 LLM 改写 SQL。"""
    try:
        llm = get_chat_llm()
        prompt = REFLECT_SYSTEM.format(
            question=question, sql=prev_sql, error=err, schema=schema
        )
        resp = llm.invoke([SystemMessage(content=prompt), HumanMessage(content="请改写")])
        m = re.search(r"\"sql\"\s*:\s*\"([\s\S]+?)\"", resp.content or "")
        if m:
            return m.group(1).replace("\\n", "\n").replace('\\"', '"')
    except Exception:
        return ""
    return ""


def _summarize_and_chart(
    question: str, sql: str, data: list[dict[str, Any]], summary_raw: str
) -> tuple[dict[str, Any], str]:
    """调用 LLM 根据 SQL + 数据生成自然语言总结 + chart_suggestion。

    失败时退化为基于列类型的简单推断。
    """
    try:
        llm = get_chat_llm()
        sample = data[:8] if data else []
        prompt = (
            SUMMARY_SYSTEM
            + "\n\n用户问题：" + question
            + "\n执行的 SQL：" + sql
            + "\n数据样本（最多 8 行）：" + json.dumps(sample, ensure_ascii=False, default=str)
            + "\n\n请用 JSON 返回：{\"summary\":\"...\",\"chart\":{\"type\":\"bar|line|pie|scatter|table\",\"title\":\"...\",\"x\":\"...\",\"y\":\"...\"}}"
            + "\n只输出一段 JSON。"
        )
        resp = llm.invoke([SystemMessage(content=prompt), HumanMessage(content=question)])
        import json as _json
        m = re.search(r"\{[\s\S]*\}", resp.content or "")
        if m:
            obj = _json.loads(m.group(0))
            return obj.get("chart") or {"type": "table"}, obj.get("summary") or (summary_raw[:200] or "已为您查询数据")
    except Exception:
        pass

    chart = _infer_chart(data)
    summary = (summary_raw or f"查询返回 {len(data)} 行数据。").strip()
    if len(summary) > 200:
        summary = summary[:200] + "…"
    return chart, summary


def _infer_chart(data: list[dict[str, Any]]) -> dict[str, Any]:
    """基于列类型简单推断图表类型。"""
    if not data:
        return {"type": "table", "title": "无数据"}
    cols = list(data[0].keys())
    if not cols:
        return {"type": "table", "title": "无列"}
    n = len(data)
    if n == 1 and len(cols) >= 2:
        # 单行多列：适合饼图
        return {"type": "pie", "title": cols[-1], "x": cols[0], "y": cols[-1]}
    # 多行多列：X 第一列，Y 其它数值列
    return {"type": "bar", "title": cols[1] if len(cols) > 1 else cols[0], "x": cols[0], "y": cols[1] if len(cols) > 1 else cols[0]}
