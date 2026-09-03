from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    app_sqlite_path: str = "./data/app.db"
    openai_api_key: str | None = None
    openai_model: str = "gpt-5-mini"
    deepseek_api_key: str | None = None
    deepseek_model: str = "deepseek-chat"
    qwen_api_key: str | None = None
    qwen_model: str = "qwen-plus"
    qwen_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"


settings = AppSettings()
