"""Environment-based configuration. All settings use the ``EMOJILENS_`` prefix."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EMOJILENS_", env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./var/emojilens.db"
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )
    # Upper bound on analysed input, in code points. Keeps per-request work bounded.
    max_input_codepoints: int = Field(default=20_000, ge=1, le=1_000_000)
    # Upper bound on a dataset upload body, in bytes.
    max_upload_bytes: int = Field(default=10 * 1024 * 1024, ge=1024)
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
