"""ARCH-01 import-boundary check (T-2.1.1; R-03, R-04, R-06, R-07).

Usage: python scripts/check_imports.py [repo_root]. Exit 1 and list violations if any.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

WEB = {"fastapi", "starlette", "uvicorn"}
# package -> top-level modules it must never import
FORBIDDEN: dict[str, set[str]] = {
    "pintae_core": WEB | {"pintae_api", "pintae_worker"},
    "pintae_rules": WEB
    | {"sqlalchemy", "pintae_core", "pintae_ingest", "pintae_api", "pintae_worker"},
    "pintae_ingest": WEB | {"sqlalchemy", "pintae_core", "pintae_api", "pintae_worker"},
    "pintae_rulepacks": WEB | {"sqlalchemy", "pintae_core", "pintae_api", "pintae_worker"},
    "pintae_api": {"pintae_worker"},
    "pintae_worker": WEB | {"pintae_api"},
}
# Shared modules that exist once, in packages/core or packages/rules; a copy in an app fails.
SINGLETON_MODULES = {
    "config.py",
    "logging.py",
    "dates.py",
    "tenancy.py",
    "status.py",
    "calendar.py",
    "engine.py",
}
LOCATIONS = {
    "pintae_core": "packages/core/pintae_core",
    "pintae_rules": "packages/rules/pintae_rules",
    "pintae_ingest": "packages/ingest/pintae_ingest",
    "pintae_rulepacks": "packages/rulepacks/pintae_rulepacks",
    "pintae_api": "apps/api/pintae_api",
    "pintae_worker": "apps/worker/pintae_worker",
}


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            out.add(node.module.split(".")[0])
    return out


def check(root: Path) -> list[str]:
    problems: list[str] = []
    for pkg, rel in LOCATIONS.items():
        base = root / rel
        if not base.exists():
            continue
        for py in sorted(base.rglob("*.py")):
            bad = _imports(py) & FORBIDDEN[pkg]
            for b in sorted(bad):
                problems.append(f"{py.relative_to(root)}: {pkg} must not import {b}")
    for app in ("apps/api", "apps/worker", "apps/web"):
        base = root / app
        if not base.exists():
            continue
        for py in sorted(base.rglob("*.py")):
            if py.name in SINGLETON_MODULES:
                problems.append(f"{py.relative_to(root)}: copy of a shared module; use the package")
    return problems


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
    problems = check(root)
    for p in problems:
        print(p)
    print("ARCH-01:", "FAIL" if problems else "ok", f"({len(problems)} violations)")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
