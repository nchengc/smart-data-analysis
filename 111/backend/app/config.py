"""配置层：Pydantic Settings 读取 .env。"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # MiniMax（兼容 OpenAI 协议）
    llm_provider: str = "minimax"
    minimax_api_key: str = ""
    minimax_base_url: str = "https://api.minimaxi.com/v1"

    # 旧：DASHSCOPE（保留字段以兼容）
    dashscope_api_key: str = ""

    # 服务器
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_debug: bool = True

    # CORS
    cors_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173"
    )

    # Phase 2+ ：模型
    qwen_chat_model: str = "MiniMax-Text-01"
    qwen_sql_model: str = "MiniMax-Text-01"
    request_timeout: int = 120

    # SQLite
    sqlite_path: str = "./data/app.db"

    # 控制
    sda_skip_init: int = 0

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
