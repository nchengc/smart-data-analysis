"""统一异常类型与错误响应。"""


class AgentError(Exception):
    """Agent 执行错误（含 LLM、SQL、解析等）。"""

    def __init__(self, message: str, *, sql: str | None = None) -> None:
        super().__init__(message)
        self.sql = sql


class ReflectLimitExceeded(AgentError):
    """Reflection 已达最大轮数。"""
