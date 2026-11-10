"""One local start command (T-2.1.2, OPS-04, R-17). Runs services directly (no Docker here).

Steps: database reachable -> migrations at head -> reference data published (idempotent) ->
worker and API started -> wait for /readyz. Any failure exits non-zero naming the service.

    python scripts/dev.py          # start and keep running until Ctrl-C
    python scripts/dev.py --check  # start, wait for readiness, stop, exit 0 or 1
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATHS = [
    ROOT / p
    for p in (
        "apps/api",
        "apps/worker",
        "packages/core",
        "packages/rules",
        "packages/rulepacks",
        "packages/ingest",
    )
]
sys.path[:0] = [str(p) for p in PATHS]

TIMEOUT_S = 180


def fail(service: str, why: str) -> int:
    print(f"not ready: {service} ({why})", file=sys.stderr)
    return 1


def main() -> int:
    check_only = "--check" in sys.argv
    from pintae_core.config import get_settings

    cfg = get_settings()
    from sqlalchemy import create_engine, text

    admin = create_engine(cfg.admin_database_url, connect_args={"connect_timeout": 5})
    try:
        with admin.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        return fail("database", type(exc).__name__)

    from alembic import command
    from alembic.config import Config

    acfg = Config(str(ROOT / "backend" / "alembic.ini"))
    acfg.attributes["url"] = cfg.admin_database_url
    try:
        command.upgrade(acfg, "head")
    except Exception as exc:
        return fail("migrations", type(exc).__name__)

    from pintae_core.publication import ensure_publisher, publish_calendar, publish_rule_pack
    from pintae_rulepacks import fixture_path, load_data
    from pintae_rules.packs import content_hash

    try:
        pub = ensure_publisher(admin, "local-publisher@vendor.localhost")
        for code in ("CAL-1", "CAL-2"):
            d = load_data(code)
            publish_calendar(admin, d, pub, content_hash(d))
        rp1 = load_data("RP-1")
        publish_rule_pack(
            admin, rp1, json.loads(fixture_path("RP-1").read_text()), pub, content_hash(rp1)
        )
    except Exception as exc:
        return fail("reference data", f"{type(exc).__name__}: {exc}")
    admin.dispose()

    env = {**os.environ, "PYTHONPATH": os.pathsep.join(str(p) for p in PATHS)}
    py = sys.executable
    procs = {
        "worker": subprocess.Popen([py, "-m", "pintae_worker.main"], env=env, cwd=ROOT),
        "api": subprocess.Popen(
            [
                py,
                "-m",
                "uvicorn",
                "pintae_api.main:app",
                "--factory",
                "--host",
                "127.0.0.1",
                "--port",
                str(cfg.api_port),
                "--no-access-log",
            ],
            env=env,
            cwd=ROOT,
        ),
    }

    def stop() -> None:
        for p in procs.values():
            if p.poll() is None:
                p.send_signal(signal.SIGTERM)
        for p in procs.values():
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()

    url = f"http://127.0.0.1:{cfg.api_port}/readyz"
    deadline = time.monotonic() + TIMEOUT_S
    last: dict[str, str] = {}
    started = time.monotonic()
    while time.monotonic() < deadline:
        for name, p in procs.items():
            if p.poll() is not None:
                stop()
                return fail(name, f"exited with {p.returncode}")
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    print(
                        f"ready in {time.monotonic() - started:.1f}s: api http://127.0.0.1:{cfg.api_port}, worker running"
                    )
                    break
        except urllib.error.HTTPError as err:
            last = json.loads(err.read() or b"{}").get("checks", {})
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            last = {"api": "not answering"}
        time.sleep(1)
    else:
        stop()
        bad = ", ".join(f"{k}: {v}" for k, v in last.items() if v != "ok") or "unknown"
        return fail(bad, f"no readiness within {TIMEOUT_S}s")

    if check_only:
        stop()
        return 0
    try:
        while all(p.poll() is None for p in procs.values()):
            time.sleep(1)
        dead = [n for n, p in procs.items() if p.poll() is not None]
        stop()
        return fail(",".join(dead), "stopped")
    except KeyboardInterrupt:
        stop()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
