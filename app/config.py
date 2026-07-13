from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    llm_provider: str | None = Field(default=None, alias="LLM_PROVIDER")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    google_api_key: str | None = Field(default=None, alias="GOOGLE_API_KEY")
    model_name: str | None = Field(default=None, alias="MODEL_NAME")
    request_timeout_seconds: float = Field(default=10.0, alias="REQUEST_TIMEOUT_SECONDS")
    max_response_bytes: int = Field(default=2_000_000, alias="MAX_RESPONSE_BYTES")
    max_redirects: int = Field(default=5, alias="MAX_REDIRECTS")
    output_directory: Path = Field(default=Path("outputs"), alias="OUTPUT_DIRECTORY")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    user_agent: str = "GEOInspector/0.1 (+https://github.com/eliandrolima/geo-inspector)"
    semantic_text_limit: int = 12_000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
