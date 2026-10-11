"""会话上下文：把历史消息拼成 LangChain 友好的 chat_history。"""

from typing import Any


def build_history_text(messages: list[dict[str, Any]], max_pairs: int = 5) -> str:
    """把最近的 N 对消息拼成短文本，作为 Agent 的上下文。"""
    user_assistant: list[dict[str, str]] = []
    for m in messages:
        if m["role"] in ("user", "assistant"):
            user_assistant.append(
                {"role": m["role"], "content": _shorten(m["content"], 200)}
            )
    # 只保留最近 max_pairs 对（成对截取）
    if len(user_assistant) > max_pairs * 2:
        user_assistant = user_assistant[-(max_pairs * 2):]
    if not user_assistant:
        return ""
    lines = ["以下是此前的对话上下文（仅供理解延续性问题）："]
    for m in user_assistant:
        role_cn = "用户" if m["role"] == "user" else "助手"
        lines.append(f"{role_cn}：{m['content']}")
    return "\n".join(lines)


def _shorten(s: str, n: int) -> str:
    s = (s or "").strip().replace("\n", " ")
    return s if len(s) <= n else s[:n] + "…"
