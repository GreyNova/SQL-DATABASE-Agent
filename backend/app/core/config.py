"""Centralized, validated application configuration (pydantic-settings)."""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration is loaded from environment / .env at startup."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- App ----
    app_name: str = "SQL Database Agent"
    app_env: Literal["local", "staging", "production"] = "local"
    app_debug: bool = False
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"

    # ---- Database ----
    database_url: str = Field(..., description="Used by migrations / admin only")
    readonly_database_url: str = Field(
        ..., description="DSN the agent uses at runtime (read-only role)"
    )

    # ---- LLM ----
    llm_provider: Literal["openai", "azure_openai", "anthropic", "gemini"] = "openai"
    openai_api_key: str = ""
    openai_api_base: str = ""
    openai_model: str = "gpt-4o"
    openai_temperature: float = 0.0
    openai_request_timeout: int = 60

    azure_openai_api_key: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_api_version: str = "2024-10-21"
    azure_openai_deployment: str = "gpt-4o"

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-sonnet-20241022"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"
    mock_llm: bool = False

    # ---- Security / guardrails ----
    sql_query_timeout_seconds: int = 15
    sql_max_rows: int = 200
    sql_forbidden_keywords: str = (
        "DROP,TRUNCATE,DELETE,UPDATE,INSERT,ALTER,GRANT,REVOKE,COPY,VACUUM,CREATE"
    )
    allow_ddl: bool = False

    # ---- CORS ----
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # ---- Observability ----
    langsmith_tracing: bool = False
    langsmith_endpoint: str = "https://api.smith.langchain.com"
    langsmith_api_key: str = ""
    langsmith_project: str = "sql-agent-prod"

    # ---- Redis (optional) ----
    redis_url: str = ""
    rate_limit_per_minute: int = 30

    # ----------------------------------------------------------------- derived
    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def forbidden_keyword_list(self) -> set[str]:
        return {k.strip().lower() for k in self.sql_forbidden_keywords.split(",") if k.strip()}

    @field_validator("openai_temperature")
    @classmethod
    def _clamp_temperature(cls, v: float) -> float:
        return max(0.0, min(v, 1.0))


@lru_cache
def get_settings() -> Settings:
    """Cached singleton — call everywhere via `get_settings()`."""
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
