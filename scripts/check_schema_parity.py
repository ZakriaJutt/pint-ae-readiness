"""Schema parity and single-head check (IT-11 parts 1-2; R-08, R-10).

Builds the ORM schema into a scratch schema of the given database and compares tables,
columns, constraints and indexes with the migrated ``public`` schema. Also fails when the
migration history has more than one head.

Usage: python scripts/check_schema_parity.py [admin_database_url]
(defaults to PINTAE_ADMIN_DATABASE_URL; run it on pintae_test or pintae_dev only).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, create_engine, text

ROOT = Path(__file__).resolve().parents[1]
SCRATCH = "parity_models"


def heads(script_location: Path) -> list[str]:
    cfg = Config()
    cfg.set_main_option("script_location", str(script_location))
    return list(ScriptDirectory.from_config(cfg).get_heads())


def _describe(engine: Engine, schema: str) -> dict[str, set[str]]:
    with engine.connect() as conn:
        cols = conn.execute(
            text(
                "SELECT table_name, column_name, data_type, udt_name, is_nullable, coalesce(column_default, '') "
                "FROM information_schema.columns WHERE table_schema = :s AND table_name <> 'alembic_version'"
            ),
            {"s": schema},
        ).all()
        cons = conn.execute(
            text(
                "SELECT rel.relname, con.conname, con.contype, pg_get_constraintdef(con.oid) "
                "FROM pg_constraint con JOIN pg_class rel ON rel.oid = con.conrelid "
                "JOIN pg_namespace n ON n.oid = rel.relnamespace "
                "WHERE n.nspname = :s AND rel.relname <> 'alembic_version'"
            ),
            {"s": schema},
        ).all()
        idx = conn.execute(
            text(
                "SELECT tablename, indexname, indexdef FROM pg_indexes WHERE schemaname = :s "
                "AND tablename <> 'alembic_version'"
            ),
            {"s": schema},
        ).all()

    def norm(v: object) -> str:
        return re.sub(rf"\b{schema}\.", "", str(v))

    return {
        "columns": {"|".join(norm(x) for x in r) for r in cols},
        "constraints": {"|".join(norm(x) for x in r) for r in cons},
        "indexes": {"|".join(norm(x) for x in r) for r in idx},
    }


def compare(engine: Engine) -> list[str]:
    sys.path[:0] = [
        str(ROOT / "packages/core"),
        str(ROOT / "packages/rules"),
        str(ROOT / "packages/ingest"),
    ]
    from pintae_core.models import Base

    with engine.begin() as conn:
        conn.execute(text(f"DROP SCHEMA IF EXISTS {SCRATCH} CASCADE"))
        conn.execute(text(f"CREATE SCHEMA {SCRATCH}"))
    scratch = engine.execution_options(schema_translate_map={None: SCRATCH})
    try:
        with scratch.begin() as conn:
            Base.metadata.create_all(conn)
        a, b = _describe(engine, "public"), _describe(engine, SCRATCH)
    finally:
        with engine.begin() as conn:
            conn.execute(text(f"DROP SCHEMA IF EXISTS {SCRATCH} CASCADE"))
    diffs: list[str] = []
    for kind in a:
        for item in sorted(a[kind] - b[kind]):
            diffs.append(f"{kind}: only in migrations: {item}")
        for item in sorted(b[kind] - a[kind]):
            diffs.append(f"{kind}: only in models: {item}")
    return diffs


def main() -> int:
    hs = heads(ROOT / "backend" / "migrations")
    if len(hs) != 1:
        print(f"FAIL: {len(hs)} migration heads: {hs}")
        return 1
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        sys.path.insert(0, str(ROOT / "packages/core"))
        from pintae_core.config import get_settings

        url = get_settings().admin_database_url
    if url.rsplit("/", 1)[-1] not in ("pintae_test", "pintae_dev"):
        print("FAIL: parity runs only on pintae_test or pintae_dev")
        return 1
    diffs = compare(create_engine(url))
    for d in diffs:
        print(d)
    print("parity:", "FAIL" if diffs else "equal", f"(head {hs[0]})")
    return 1 if diffs else 0


if __name__ == "__main__":
    raise SystemExit(main())
