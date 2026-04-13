"""Application configuration via pydantic-settings."""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Core
    app_name: str = "contract-centry"
    env: str = Field("development", description="development|staging|production")
    log_level: str = "INFO"

    # DB
    database_url: str = "sqlite+aiosqlite:///./contract_centry.db"

    # Celery / Redis
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # Sandbox defaults
    sandbox_cpu: str = "2"
    sandbox_memory: str = "4g"
    static_analysis_timeout_s: int = 300
    dynamic_analysis_timeout_s: int = 600
    simulation_timeout_s: int = 900

    # Upload limits
    max_contract_bytes: int = 512 * 1024

    # Fork
    fork_rpc_url: str | None = None

    # Analysis tool binaries
    slither_bin: str = "slither"
    mythril_bin: str = "myth"
    echidna_bin: str = "echidna-test"
    forge_bin: str = "forge"
    anvil_bin: str = "anvil"


@lru_cache
def get_settings() -> Settings:
    return Settings()
