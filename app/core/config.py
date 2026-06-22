"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = Field(default="leadfinder", alias="APP_NAME")
    app_env: Literal["development", "staging", "production"] = Field(
        default="development",
        alias="APP_ENV",
    )
    debug: bool = Field(default=False, alias="DEBUG")
    secret_key: str = Field(default="change-me", alias="SECRET_KEY")

    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")

    database_url: str = Field(
        default="postgresql+psycopg://leadfinder:leadfinder@localhost:5432/leadfinder",
        alias="DATABASE_URL",
    )
    redis_url: RedisDsn = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: Literal["console", "json"] = Field(default="console", alias="LOG_FORMAT")

    worker_concurrency: int = Field(default=2, alias="WORKER_CONCURRENCY")
    inspection_browser_enabled: bool = Field(default=False, alias="INSPECTION_BROWSER_ENABLED")
    inspection_browser_concurrency: int = Field(default=1, alias="INSPECTION_BROWSER_CONCURRENCY")
    inspection_timeout_seconds: int = Field(default=30, alias="INSPECTION_TIMEOUT_SECONDS")
    job_queue_name: str = Field(default="leadfinder:jobs:queue", alias="JOB_QUEUE_NAME")
    job_max_retries: int = Field(default=3, alias="JOB_MAX_RETRIES")
    job_retry_delay_seconds: int = Field(default=5, alias="JOB_RETRY_DELAY_SECONDS")
    worker_poll_seconds: int = Field(default=5, alias="WORKER_POLL_SECONDS")
    scheduler_poll_seconds: int = Field(default=60, alias="SCHEDULER_POLL_SECONDS")

    inspection_queue_name: str = Field(default="leadfinder:inspection:queue", alias="INSPECTION_QUEUE_NAME")
    inspection_save_artifacts: bool = Field(default=True, alias="INSPECTION_SAVE_ARTIFACTS")

    data_dir: Path = Field(default=Path("./data"), alias="DATA_DIR")
    export_dir: Path = Field(default=Path("./data/exports"), alias="EXPORT_DIR")

    tomtom_enabled: bool = Field(default=False, alias="TOMTOM_ENABLED")
    tomtom_api_key: str | None = Field(default=None, alias="TOMTOM_API_KEY")
    tomtom_timeout_seconds: int = Field(default=15, alias="TOMTOM_TIMEOUT_SECONDS")
    tomtom_search_radius_meters: int = Field(default=15000, alias="TOMTOM_SEARCH_RADIUS_METERS")

    @property
    def snapshots_dir(self) -> Path:
        return self.data_dir / "snapshots"

    @property
    def screenshots_dir(self) -> Path:
        return self.data_dir / "screenshots"

    @field_validator("data_dir", "export_dir", mode="before")
    @classmethod
    def parse_path(cls, value: str | Path) -> Path:
        return Path(value)

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def sqlalchemy_database_url(self) -> str:
        """Return SQLAlchemy-compatible database URL string."""
        return self.database_url


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance for dependency injection."""
    return Settings()
