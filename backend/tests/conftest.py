"""Test configuration. Integration tests use pintae_test only, through the pintae_app role
(NOSUPERUSER NOBYPASSRLS); the owner role is used only to rebuild the schema and to seed."""

from __future__ import annotations

import base64
import os
import secrets

os.environ.setdefault("PINTAE_ENV", "test")
# Sign-in keys for this test process only (random, never stored) when no backend/.env exists.
os.environ.setdefault("PINTAE_SECRET_KEY", secrets.token_urlsafe(48))
os.environ.setdefault("PINTAE_TOTP_KEY", base64.b64encode(os.urandom(32)).decode())
os.environ.setdefault(
    "PINTAE_DATABASE_URL", "postgresql+psycopg://pintae_app@localhost:5432/pintae_test"
)
os.environ.setdefault(
    "PINTAE_ADMIN_DATABASE_URL", "postgresql+psycopg://zakria@localhost:5432/pintae_test"
)
