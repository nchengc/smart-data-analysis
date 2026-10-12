"""LLM 客户端：通过 OpenAI 兼容协议统一接入多家 LLM。

当前默认走 minimax（MiniMax），可通过 .env 的 LLM_PROVIDER 切换 dashscope。
"""

from functools import lru_cache

from langchain_community.chat_models import ChatTongyi
from langchain_openai import ChatOpenAI

from app.config import get_settings


def _common_kwargs() -> dict:
    s = get_settings()
    return {"temperature": 0.1, "timeout": s.request_timeout, "max_retries": 2}


@lru_cache
def get_chat_llm():
    """对话主模型（理解、规划、总结）。"""
    s = get_settings()
    if s.llm_provider == "dashscope" and s.dashscope_api_key:
        return ChatTongyi(
            model=s.qwen_chat_model,
            api_key=s.dashscope_api_key,
            **_common_kwargs(),
        )
    # 默认 minimax（OpenAI 兼容协议）
    return ChatOpenAI(
        model=s.qwen_chat_model,
        openai_api_key=s.minimax_api_key or "EMPTY",
        openai_api_base=s.minimax_base_url,
        **_common_kwargs(),
    )


@lru_cache
def get_sql_llm():
    """SQL 生成特化模型。"""
    s = get_settings()
    if s.llm_provider == "dashscope" and s.dashscope_api_key:
        return ChatTongyi(
            model=s.qwen_sql_model,
            api_key=s.dashscope_api_key,
            temperature=0.0,
            timeout=s.request_timeout,
            max_retries=2,
        )
    # 默认 minimax
    return ChatOpenAI(
        model=s.qwen_sql_model,
        openai_api_key=s.minimax_api_key or "EMPTY",
        openai_api_base=s.minimax_base_url,
        temperature=0.0,
        timeout=s.request_timeout,
        max_retries=2,
    )
