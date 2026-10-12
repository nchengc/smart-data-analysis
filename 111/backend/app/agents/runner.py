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
from app.agents.prompts import (
    FOLLOWUP_KEYWORDS,
    FOLLOWUP_SYSTEM,
    REFLECT_SYSTEM,
    SQL_GEN_SYSTEM,
    SUMMARY_SYSTEM,
)
from app.agents.sql_agent import build_sql_agent, extract_json_obj
from app.db.engine import get_engine
from app.db.metadata import get_schema_text
from app.db import session_store
from app.llm.client import get_chat_llm, get_sql_llm
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
    mode: str = "full"  # 'full' | 'followup' | 'chart_only'


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


def _is_followup(question: str) -> bool:
    """检测当前问题是否是对上一轮的追问。"""
    if not question:
        return False
    return any(kw in question for kw in FOLLOWUP_KEYWORDS)


def _is_chart_only_followup(question: str) -> bool:
    """用户只要求换图表类型，不修改 SQL。"""
    chart_swap_kw = ("换成", "改为", "切到", "变成", "用", "展示为", "画成")
    if not any(kw in question for kw in chart_swap_kw):
        return False
    chart_type_kw = ("柱状", "折线", "饼", "散点", "表格", "条形", "区域", "bar", "line", "pie", "scatter", "table")
    return any(kw in question.lower() for kw in chart_type_kw) or any(
        kw in question for kw in ("柱状图", "折线图", "饼图", "散点图", "表格图", "条形图", "面积图", "柱图", "饼状图")
    )


def _run_sql_with_reflect(
    sql: str, question: str, schema: str, max_reflect: int
) -> tuple[str, list[dict[str, Any]], int, int, str | None]:
    """SQL 校验 + 执行（带 Reflection）。返回 (sql, data, row_count, reflect_rounds, error)。"""
    reflect_round = 0
    while True:
        try:
            sql = normalize_sql(sql)
            validate_select_only(sql)
            sql = ensure_limit(sql, default_limit=1000)
            data, row_count = _exec_sql(sql)
            return sql, data, row_count, reflect_round, None
        except SQLSecurityError as e:
            return (
                "SELECT 'security_blocked' AS x;",
                [{"x": "blocked"}],
                1,
                reflect_round,
                f"SQL 安全拒绝：{e}",
            )
        except Exception as e:
            reflect_round += 1
            if reflect_round > max_reflect:
                return (
                    "SELECT 'error' AS x;",
                    [{"x": "error"}],
                    1,
                    reflect_round,
                    f"Reflection 失败（{max_reflect} 轮）：{e}",
                )
            new_sql = _reflect_sql(question, sql, str(e), schema)
            if not new_sql:
                # LLM 改写失败，直接 break
                return (
                    sql,
                    [],
                    0,
                    reflect_round,
                    f"SQL 改写失败：{e}",
                )
            sql = new_sql


# ---- Chart type 切换（仅换图）----

_CHART_TYPE_MAP = {
    # 中文
    "柱状": "bar", "柱状图": "bar", "柱图": "bar", "条形": "bar", "条形图": "bar",
    "折线": "line", "折线图": "line", "线图": "line", "面积": "line", "面积图": "line",
    "饼": "pie", "饼图": "pie", "饼状": "pie", "饼状图": "pie",
    "散点": "scatter", "散点图": "scatter",
    "表格": "table", "表格图": "table",
    # 英文
    "bar": "bar", "line": "line", "pie": "pie", "scatter": "scatter", "table": "table",
}


def _chart_type_cn(t: str) -> str:
    return {
        "bar": "柱状图",
        "line": "折线图",
        "pie": "饼图",
        "scatter": "散点图",
        "table": "表格",
    }.get(t, t)


def _swap_chart_type(question: str, prev_chart: dict[str, Any]) -> dict[str, Any]:
    """从用户问题里识别要切到的目标 chart type。"""
    lower = question.lower()
    for kw, ctype in _CHART_TYPE_MAP.items():
        if kw in lower or kw in question:
            return {**prev_chart, "type": ctype}
    return prev_chart


def _simple_summary(msg: str) -> str:
    return msg.strip()


def run_chat(session_id: str, question: str, *, max_reflect: int = 2) -> ChatRunResult:
    """主入口：传入 session_id + 问题，返回结果。

    会同时把 user/assistant 消息持久化到 session_store。
    """
    started = time.time()
    history_messages = session_store.list_messages(session_id, limit=20)
    history_text = build_history_text(history_messages)
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

    # 找上一轮 assistant 消息（用于追问 / 换图）
    last_assistant = None
    for m in reversed(history_messages):
        if m.get("role") == "assistant":
            last_assistant = m
            break

    chart: dict[str, Any] = {"type": "table", "title": ""}
    sql = ""
    summary = ""
    data: list[dict[str, Any]] = []
    row_count = 0
    error: str | None = None
    reflect_round = 0
    mode = "full"

    # 决策：是新建查询 / 追问改写 / 仅换图
    chart_only = bool(last_assistant) and _is_chart_only_followup(question)
    is_followup = (not chart_only) and bool(last_assistant) and _is_followup(question)

    if chart_only and last_assistant:
        # 路径 3：仅换图表类型。复用上一轮的 SQL + data
        mode = "chart_only"
        sql = last_assistant.get("sql") or "SELECT 'no_sql' AS x;"
        try:
            data, row_count = _exec_sql(sql)
        except Exception:
            # 上一轮 SQL 失败时不报错；用上次数据
            data = last_assistant.get("data") or []
            row_count = len(data)
        # 推断目标 chart type
        new_chart = _swap_chart_type(question, last_assistant.get("chart") or chart)
        chart = new_chart
        # 用 LLM 生成自然语言 summary（说明换图）
        summary = _simple_summary("已切换为 " + _chart_type_cn(new_chart.get("type", "table")) + " 展示。")
        raw = ""

    elif is_followup and last_assistant:
        # 路径 2：基于上一轮 SQL 改写
        mode = "followup"
        prev_sql = last_assistant.get("sql") or ""
        prev_data = (last_assistant.get("data") or [])[:8]
        prev_sample = json.dumps(prev_data, ensure_ascii=False, default=str)
        try:
            llm = get_chat_llm()
            followup_prompt = FOLLOWUP_SYSTEM.format(
                history_block=history_text or "（无）",
                prev_sql=prev_sql,
                prev_sample=prev_sample,
                question=question,
            )
            from langchain_core.messages import HumanMessage, SystemMessage
            resp = llm.invoke([
                SystemMessage(content=followup_prompt),
                HumanMessage(content=question),
            ])
            raw = resp.content or ""
        except Exception as e:
            raw = ""
            error = f"追问 LLM 失败：{e}"
        # 解析 JSON
        obj = extract_json_obj(raw)
        sql = obj.get("sql") or prev_sql
        if obj.get("chart"):
            chart = obj["chart"]
        summary = obj.get("summary") or ""

        # SQL 校验 + 执行（带 reflection）
        sql, data, row_count, reflect_round, sql_err = _run_sql_with_reflect(
            sql, question, schema, max_reflect
        )
        if sql_err:
            error = sql_err

    else:
        # 路径 1：完整新建查询
        mode = "full"
        # 1) 用 ChatOpenAI/ChatTongyi 直接生成 JSON（避开 LangChain Agent 格式不兼容）
        try:
            llm = get_sql_llm()
            from langchain_core.messages import HumanMessage, SystemMessage
            full_prompt = SQL_GEN_SYSTEM.format(schema=schema) + (
                f"\n\n对话上下文：\n{history_text}\n\n用户问题：{question}\n"
                if history_text
                else f"\n\n用户问题：{question}\n"
            )
            resp = llm.invoke([
                SystemMessage(content=full_prompt),
                HumanMessage(content=question),
            ])
            raw = resp.content or ""
        except Exception as e:
            raw = ""
            error = f"LLM 调用失败：{e}"

        # 2) 解析 JSON 拿 SQL
        import json as _json
        obj = extract_json_obj(raw)
        if obj.get("sql"):
            sql = obj["sql"]
            if obj.get("chart") and isinstance(obj["chart"], dict):
                chart = obj["chart"]
            if obj.get("summary"):
                # 稍后会被 _summarize_and_chart 覆盖，这里先用
                pass
        else:
            sql = _extract_sql_from_agent_text(raw)

        # 3) SQL 校验 + 执行（带 Reflection）
        sql, data, row_count, reflect_round, sql_err = _run_sql_with_reflect(
            sql, question, schema, max_reflect
        )
        if sql_err:
            error = sql_err

        # 4) 调用 LLM 总结 + 选图表
        if not sql_err:
            chart, summary = _summarize_and_chart(question, sql, data, raw)
        else:
            chart = _infer_chart(data)
            summary = f"未能成功执行查询：{sql_err}"

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
        mode=mode,
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
