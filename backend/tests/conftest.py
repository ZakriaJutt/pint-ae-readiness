"""Test configuration. Integration tests use pintae_test only, through the pintae_app role
(NOSUPERUSER NOBYPASSRLS); the owner role is used only to rebuild the schema and to seed."""

from __future__ import annotations

import os

os.environ.setdefault("PINTAE_ENV", "test")
os.environ.setdefault(
    "PINTAE_DATABASE_URL", "postgresql+psycopg://pintae_app@localhost:5432/pintae_test"
)
os.environ.setdefault(
    "PINTAE_ADMIN_DATABASE_URL", "postgresql+psycopg://zakria@localhost:5432/pintae_test"
)
