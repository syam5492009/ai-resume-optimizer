"""
src/utils/config.py
--------------------
Settings loaded from .env file.
Supports Anthropic Claude and OpenAI as AI providers.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # AI Provider — choose "anthropic" or "openai"
    AI_PROVIDER: Literal["anthropic", "openai"] = "anthropic"

    # Anthropic (Claude) — get key at console.anthropic.com
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-6"

    # OpenAI — get key at platform.openai.com
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Output settings
    OUTPUT_DIR: str = "outputs"
    MAX_RESUME_SIZE_MB: int = 10


settings = Settings()
