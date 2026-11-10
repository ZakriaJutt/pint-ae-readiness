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
    assert Settings(env="production", public_base_url="https://desk.example.ae").env == "production"
    assert Settings(env="local").public_base_url.startswith("http://localhost")


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
