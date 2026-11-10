"""Engines. The application engine uses the NOSUPERUSER NOBYPASSRLS role; the admin engine is
for migrations and vendor publication scripts only."""

from __future__ import annotations

from functools import lru_cache

from sqlalchemy import Engine, create_engine

from pintae_core.config import get_settings


@lru_cache(maxsize=4)
def engine_for(url: str) -> Engine:
    return create_engine(url, pool_pre_ping=True, future=True)


def app_engine() -> Engine:
    return engine_for(get_settings().database_url)


def admin_engine() -> Engine:
    return engine_for(get_settings().admin_database_url)
