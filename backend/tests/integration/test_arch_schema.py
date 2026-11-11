"""ARCH-01 (import boundaries, seeded violations) and IT-11 parts 1-2 (parity, single head)."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from scripts import check_imports, check_schema_parity
from sqlalchemy import Engine, text

ROOT = Path(__file__).resolve().parents[3]


def test_arch01_repository_is_clean() -> None:
    assert check_imports.check(ROOT) == []


def test_arch01_seeded_violations_fail(tmp_path: Path) -> None:
    for rel in check_imports.LOCATIONS.values():
        shutil.copytree(ROOT / rel, tmp_path / rel)
    (tmp_path / "apps/api/pintae_api/bad.py").write_text("from pintae_worker import handlers\n")
    (tmp_path / "apps/worker/pintae_worker/config.py").write_text("MAX = 1\n")
    (tmp_path / "packages/core/pintae_core/bad.py").write_text("import fastapi\n")
    (tmp_path / "apps/worker/pintae_worker/web.py").write_text(
        "from starlette.requests import Request\n"
    )
    problems = "\n".join(check_imports.check(tmp_path))
    assert "pintae_api must not import pintae_worker" in problems
    assert "pintae_worker/config.py: copy of a shared module" in problems
    assert "pintae_core must not import fastapi" in problems
    assert "pintae_worker must not import starlette" in problems


def test_worker_starts_without_web_modules() -> None:
    code = (
        "import sys; import pintae_worker.main; "
        "bad = [m for m in ('fastapi', 'starlette', 'uvicorn', 'pintae_api') if m in sys.modules]; "
        "print(bad); sys.exit(1 if bad else 0)"
    )
    paths = ":".join(
        str(ROOT / p)
        for p in (
            "apps/worker",
            "packages/core",
            "packages/rules",
            "packages/ingest",
            "packages/rulepacks",
        )
    )
    r = subprocess.run(
        [sys.executable, "-c", code],
        env={"PYTHONPATH": paths, "PATH": "/usr/bin"},
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr


def test_it11_parity_equal_and_drift_detected(admin_engine: Engine) -> None:
    assert check_schema_parity.compare(admin_engine) == []
    with admin_engine.begin() as conn:
        conn.execute(text("CREATE INDEX ix_drift ON findings (dataset)"))
    try:
        diffs = check_schema_parity.compare(admin_engine)
        assert any("ix_drift" in d and "only in migrations" in d for d in diffs)
    finally:
        with admin_engine.begin() as conn:
            conn.execute(text("DROP INDEX ix_drift"))


def test_it11_single_head_and_two_heads_fail(tmp_path: Path) -> None:
    src = ROOT / "backend/migrations"
    assert check_schema_parity.heads(src) == ["0005"]
    dst = tmp_path / "migrations"
    shutil.copytree(src, dst)
    for rev in ("0002a", "0002b"):
        (dst / "versions" / f"{rev}.py").write_text(
            f'revision = "{rev}"\ndown_revision = "0005"\nbranch_labels = None\ndepends_on = None\n'
            "def upgrade():\n    pass\ndef downgrade():\n    pass\n"
        )
    assert sorted(check_schema_parity.heads(dst)) == ["0002a", "0002b"]
