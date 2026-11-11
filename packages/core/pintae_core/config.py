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

    # B2 sign-in (TRD 8.1). Keys come from the gitignored backend/.env locally and from the
    # secret store elsewhere; only their names are in backend/.env.example.
    secret_key: str = ""  # HMAC key: anti-forgery tokens and throttle-key hashing
    totp_key: str = ""  # base64 of 32 bytes: AES-GCM key for users.totp_secret_enc
    session_absolute_hours: int = 12
    session_pending_minutes: int = 10  # between the password step and the TOTP step
    invite_valid_hours: int = 24
    password_reset_valid_minutes: int = 20
    throttle_window_minutes: int = 15
    # B2-S01, B2-S04: reserved atomically before a factor is verified (migration 0008).
    throttle_account_failures: int = 5  # failures per (account, client address) per window
    throttle_client_attempts: int = 30  # sign-in requests per client address per window
    throttle_account_clients: int = 5  # distinct failing addresses before the account delay
    throttle_delay_base_seconds: int = 30  # account delay, doubling per further address
    throttle_delay_cap_seconds: int = 300  # the account delay never exceeds this
    reset_mails_per_window: int = 3  # reset mails to one address per window; more are dropped
    totp_failures_per_session: int = 5

    # B2 e-mail: SMTP; locally the Mailpit inbox at 127.0.0.1:1025 without authentication.
    smtp_host: str = "127.0.0.1"
    smtp_port: int = 1025
    smtp_starttls: bool = False
    smtp_username: str | None = None
    smtp_password: str | None = None
    mail_from: str = "PINT AE Readiness Desk <no-reply@pintae.invalid>"

    # B2 object storage: "local" (directory fake, tests) or "s3" (MinIO locally, S3 later).
    storage_backend: str = "local"
    s3_endpoint_url: str | None = None
    s3_region: str = "us-east-1"
    s3_bucket: str = "pintae-dev"
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None

    @model_validator(mode="after")
    def _sign_in_keys_present(self) -> Settings:
        import base64
        import binascii

        if len(self.secret_key) < 32:
            raise ValueError("PINTAE_SECRET_KEY must be set (at least 32 characters)")
        try:
            raw = base64.b64decode(self.totp_key, validate=True)
        except binascii.Error as exc:
            raise ValueError("PINTAE_TOTP_KEY must be base64") from exc
        if len(raw) != 32:
            raise ValueError("PINTAE_TOTP_KEY must be base64 of 32 bytes")
        if self.storage_backend not in ("local", "s3"):
            raise ValueError("PINTAE_STORAGE_BACKEND must be local or s3")
        if self.storage_backend == "s3" and not (
            self.s3_access_key_id and self.s3_secret_access_key
        ):
            raise ValueError("PINTAE_S3_ACCESS_KEY_ID and PINTAE_S3_SECRET_ACCESS_KEY are required")
        if self.env not in ("local", "test") and self.storage_backend != "s3":
            raise ValueError("PINTAE_STORAGE_BACKEND must be s3 outside local and test")
        return self

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
