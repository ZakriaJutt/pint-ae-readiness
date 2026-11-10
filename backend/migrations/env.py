"""Alembic environment. Migrations run as the owner role (PINTAE_ADMIN_DATABASE_URL), never
as the application role. One linear history (R-10)."""

from __future__ import annotations

from alembic import context
from sqlalchemy import create_engine

from pintae_core.config import get_settings
from pintae_core.models import Base

target_metadata = Base.metadata


def run_migrations_online() -> None:
    url = context.config.attributes.get("url") or get_settings().admin_database_url
    engine = create_engine(url)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


run_migrations_online()
