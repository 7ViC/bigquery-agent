"""
Central configuration — loads from .env and provides typed settings.
"""

from __future__ import annotations

import os
from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """All application settings, loaded from .env automatically."""

    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- GCP ---
    gcp_project_id: str = ""
    gcp_location: str = "us-central1"
    google_application_credentials: str = "config/service-account.json"

    # --- BigQuery ---
    bq_dataset: str = "autoanalyst"

    # --- LLM ---
    llm_provider: str = "gemini"  # "gemini" or "openai"
    gemini_model: str = "gemini-2.0-flash"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    # --- API ---
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # --- Dashboard ---
    dashboard_port: int = 8501

    # --- Logging ---
    log_level: str = "INFO"

    @property
    def credentials_path(self) -> Path:
        p = Path(self.google_application_credentials)
        if not p.is_absolute():
            p = ROOT_DIR / p
        return p


@lru_cache()
def get_settings() -> Settings:
    """Cached singleton settings instance."""
    return Settings()
