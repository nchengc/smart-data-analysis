"""LLM 客户端：LangChain ChatTongyi（阿里云百炼 Qwen3 系列）。"""

from functools import lru_cache

from langchain_community.chat_models import ChatTongyi

from app.config import get_settings


@lru_cache
def get_chat_llm() -> ChatTongyi:
    """对话主模型（理解、规划、总结）。"""
    s = get_settings()
    return ChatTongyi(
        model=s.qwen_chat_model,
        api_key=s.dashscope_api_key,
        temperature=0.1,
        timeout=s.request_timeout,
        max_retries=2,
    )


@lru_cache
def get_sql_llm() -> ChatTongyi:
    """SQL 生成特化模型。"""
    s = get_settings()
    return ChatTongyi(
        model=s.qwen_sql_model,
        api_key=s.dashscope_api_key,
        temperature=0.0,
        timeout=s.request_timeout,
        max_retries=2,
    )
