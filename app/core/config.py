"""Application configuration."""

import os
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "Matapan"
    app_version: str = "0.1.0"
    debug: bool = False

    # Database
    database_url: str = "sqlite:///./matapan.db"

    # API
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:3000"]

    # FX Rates
    fx_api_key: str = ""
    fx_api_base_url: str = "https://api.freecurrencyapi.com/v1"

    # Ollama (AI)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"

    # Reporting currency (for FX conversions)
    reporting_currency: str = "CHF"

    class Config:
        """Pydantic config."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
