"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "DEUS Bank Support API"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    # OpenAI STT model for /chat/voice (no local weights). whisper-1 is the simple default.
    whisper_model: str = "whisper-1"
    # "mock" = no external LLM calls; "openai" = LangChain ChatOpenAI
    llm_mode: str = "mock"


@lru_cache
def get_settings() -> Settings:
    return Settings()
