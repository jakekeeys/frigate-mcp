"""Configuration for Frigate MCP Server."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Server settings loaded from environment variables."""

    frigate_url: str = Field(
        default="http://localhost:5000",
        alias="FRIGATE_URL",
        description="Base URL of the Frigate instance (e.g. http://192.168.1.50:5000)",
    )
    timeout: int = Field(
        default=30,
        alias="FRIGATE_TIMEOUT",
        description="HTTP request timeout in seconds",
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    """Get cached settings singleton."""
    return Settings()
