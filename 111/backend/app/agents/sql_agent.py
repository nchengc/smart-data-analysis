"""LangChain SQL Agent 封装。"""

from __future__ import annotations

import json
import re
from typing import Any

from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits.sql.base import create_sql_agent

from app.db.metadata import get_sql_database
from app.llm.client import get_sql_llm


def build_sql_agent(db: SQLDatabase | None = None):  # noqa: ANN001 - LangChain type opaque
    db = db or get_sql_database()
    llm = get_sql_llm()

    toolkit = SQLDatabaseToolkit(db=db, llm=llm)

    agent = create_sql_agent(
        llm=llm,
        toolkit=toolkit,
        verbose=False,
        handle_parsing_errors=True,
        max_iterations=5,
        early_stopping_method="force",
    )
    return agent


# ---- JSON 解析工具 ----
_JSON_RE = re.compile(r"\{[\s\S]*\}")


def extract_json_obj(text: str) -> dict[str, Any]:
    """从 LLM 输出里尽量抽出 JSON 对象。"""
    if not text:
        return {}
    m = _JSON_RE.search(text)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except Exception:
        return {}
