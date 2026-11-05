"""Application settings loaded exclusively from environment variables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "PlaceMate API"
    env: str = "development"
    debug: bool = False
    demo_mode: bool = False
    policy_version: str = "2026-01"

    # URLs
    frontend_url: str = "http://localhost:3000"
    api_public_url: str = "http://localhost:8000"
    cors_origins: str = "http://localhost:3000"

    # Data stores
    database_url: str = "sqlite:///./placemate.db"
    redis_url: str = "redis://localhost:6379/0"

    # Auth
    jwt_secret: str = Field(
        default="insecure-development-only-secret-change-me",
        min_length=16,
    )
    access_token_minutes: int = 15
    refresh_token_days: int = 14
    auth_google_client_id: str = ""
    auth_google_client_secret: str = ""

    # LLM
    llm_provider: str = "mock"
    llm_api_key: str = ""
    google_application_credentials: str = ""
    google_cloud_project: str = ""
    google_cloud_location: str = "us-central1"
    llm_model_cheap: str = "gemini-2.0-flash-001"
    llm_model_scoring: str = "gemini-2.5-pro"
    llm_embedding_model: str = "text-embedding-004"
    llm_base_url: str = "https://api.openai.com/v1"
    embedding_dim: int = 768
    scoring_samples: int = 3
    scoring_max_retries: int = 2
    scoring_temperature: float = 0.2
    mock_llm_hallucinate: bool = False

    # Storage
    storage_backend: str = "local"
    storage_endpoint: str = "http://localhost:9000"
    storage_bucket: str = "placemate-resumes"
    storage_key: str = ""
    storage_secret: str = ""
    storage_region: str = "auto"
    storage_secure: bool = False
    storage_local_dir: str = "./storage/uploads"

    # Limits
    max_upload_mb: int = 5
    per_user_monthly_budget: float = 1.50
    rate_limit_default: str = "120/minute"
    rate_limit_auth: str = "10/minute"
    rate_limit_upload: str = "10/minute"
    rate_limit_analysis: str = "12/minute"
    rate_limit_interview: str = "10/minute"
    rate_limit_storage_uri: str = "memory://"

    # Observability
    sentry_dsn: str = ""
    posthog_key: str = ""
    posthog_host: str = "https://us.i.posthog.com"
    log_level: str = "INFO"

    @property
    def allowed_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
