"""Settings validation (OPS-05 start refusal, local part) and OPS-04 failure naming."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from pintae_core.config import Settings

ROOT = Path(__file__).resolve().parents[3]


def test_public_url_must_be_https_public_outside_local() -> None:
    with pytest.raises(ValidationError, match="https"):
        Settings(env="production", public_base_url="http://desk.example.ae")
    with pytest.raises(ValidationError, match="public host"):
        Settings(env="staging", public_base_url="https://localhost")
    prod = Settings(
        env="production",
        public_base_url="https://desk.example.ae",
        storage_backend="s3",
        s3_access_key_id="k",
        s3_secret_access_key="s",
        s3_region="me-central-1",
    )
    assert prod.env == "production"
    assert Settings(env="local").public_base_url.startswith("http://localhost")


def test_b2_sign_in_keys_and_storage_backend_are_validated() -> None:
    with pytest.raises(ValidationError, match="PINTAE_SECRET_KEY"):
        Settings(secret_key="short")
    with pytest.raises(ValidationError, match="PINTAE_TOTP_KEY"):
        Settings(totp_key="AAAA")
    with pytest.raises(ValidationError, match="s3 outside local"):
        Settings(
            env="production", public_base_url="https://desk.example.ae", storage_backend="local"
        )
    with pytest.raises(ValidationError, match="ACCESS_KEY_ID"):
        Settings(storage_backend="s3", s3_access_key_id=None, s3_secret_access_key=None)


def test_c2_storage_region_must_be_in_the_uae_outside_local() -> None:
    """compliance/self-check.md section 4: client files never leave a UAE region."""

    def make(env: str, region: str) -> Settings:
        return Settings(
            env=env,
            public_base_url="https://desk.example.ae",
            storage_backend="s3",
            s3_access_key_id="k",
            s3_secret_access_key="s",
            s3_region=region,
        )

    # me-south-1 is AWS Bahrain and me-central1 is Google Doha: near, but not in the UAE.
    for region in ("us-east-1", "me-south-1", "me-central1", "ca-central-1", ""):
        for env in ("staging", "production"):
            with pytest.raises(ValidationError, match="UAE region"):
                make(env, region)
    for region in ("me-central-1", "uaenorth", "uaecentral"):
        assert make("production", region).s3_region == region
    # Local MinIO keeps its own region; the rule binds staging and production only.
    assert make("local", "us-east-1").s3_region == "us-east-1"
    assert make("test", "us-east-1").s3_region == "us-east-1"


def test_ops04_start_fails_naming_the_database() -> None:
    env = {
        **os.environ,
        "PINTAE_ADMIN_DATABASE_URL": "postgresql+psycopg://zakria@localhost:5499/pintae_dev",
    }
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts/dev.py"), "--check"],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert r.returncode == 1
    assert "not ready: database" in r.stderr
