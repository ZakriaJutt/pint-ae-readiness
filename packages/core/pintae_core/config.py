"""Settings, read once and validated at start (TRD section 7). The only config module (R-06)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PINTAE_",
        env_file=str(REPO_ROOT / "backend" / ".env"),
        extra="ignore",
    )

    env: str = "local"  # local, test, staging, production
    # Application role: NOSUPERUSER NOBYPASSRLS. Used by the API and the worker.
    database_url: str = "postgresql+psycopg://pintae_app@localhost:5432/pintae_dev"
    # Owner role: migrations and vendor publication scripts only, never the API or worker.
    admin_database_url: str = "postgresql+psycopg://zakria@localhost:5432/pintae_dev"
    storage_root: Path = REPO_ROOT / "var" / "storage"
    public_base_url: str = "http://localhost:3105"
    api_port: int = 8105
    # Assigned to this product but unused: TRD AD-02 keeps jobs in PostgreSQL, no Redis.
    redis_db_index: int = 4
    max_upload_bytes: int = 20 * 1024 * 1024
    max_xlsx_uncompressed_bytes: int = 200 * 1024 * 1024
    max_rows: int = 200_000
    stale_after_days: int = 45
    job_lease_seconds: int = 300
    worker_heartbeat_max_age_seconds: int = 30

    @model_validator(mode="after")
    def _public_url_is_https_outside_local(self) -> Settings:
        parsed = urlparse(self.public_base_url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("PINTAE_PUBLIC_BASE_URL must be an absolute URL")
        if self.env not in ("local", "test"):
            if parsed.scheme != "https":
                raise ValueError("PINTAE_PUBLIC_BASE_URL must use https outside local")
            if parsed.hostname in ("localhost", "127.0.0.1", "::1"):
                raise ValueError("PINTAE_PUBLIC_BASE_URL must be a public host outside local")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
