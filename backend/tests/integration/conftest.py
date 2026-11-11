"""Integration fixtures: a freshly migrated pintae_test, published CAL-1, CAL-2 and RP-1,
and helpers that seed firms, users and sessions.

The seeded sessions are the test-only stand-in for signing in (the B1 fake): they are real
``sessions`` rows used through the real cookie and anti-forgery checks. The sign-in flow
itself is tested end to end in ``test_b2_sign_in.py`` against Mailpit."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text

from pintae_api.deps import SESSION_COOKIE
from pintae_api.main import create_app
from pintae_core import background
from pintae_core.auth import csrf_token
from pintae_core.config import get_settings
from pintae_core.models import TENANT_TABLES
from pintae_core.publication import ensure_publisher, publish_calendar, publish_rule_pack
from pintae_core.storage import LocalObjectStore, ObjectStore
from pintae_rulepacks import load_data
from pintae_rules.packs import content_hash
from pintae_worker.main import run_once
from tests.helpers import rp1_cases

BACKEND = Path(__file__).resolve().parents[2]


def _assert_test_db(url: str) -> None:
    assert url.rsplit("/", 1)[-1] == "pintae_test", "integration tests run only against pintae_test"


@pytest.fixture(scope="session")
def admin_engine() -> Iterator[Engine]:
    url = get_settings().admin_database_url
    _assert_test_db(url)
    eng = create_engine(url)
    with eng.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        conn.execute(text("GRANT USAGE ON SCHEMA public TO PUBLIC"))
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.attributes["url"] = url
    command.upgrade(cfg, "head")
    yield eng
    eng.dispose()


@pytest.fixture(scope="session")
def publisher_id(admin_engine: Engine) -> uuid.UUID:
    return ensure_publisher(admin_engine, "publisher@vendor.test")


@pytest.fixture(scope="session")
def published(admin_engine: Engine, publisher_id: uuid.UUID) -> None:
    for code in ("CAL-1", "CAL-2"):
        data = load_data(code)
        publish_calendar(admin_engine, data, publisher_id, content_hash(data))
    rp1 = load_data("RP-1")
    publish_rule_pack(admin_engine, rp1, rp1_cases(), publisher_id, content_hash(rp1))


@pytest.fixture(scope="session")
def app_engine(admin_engine: Engine, published: None) -> Iterator[Engine]:
    url = get_settings().database_url
    _assert_test_db(url)
    eng = create_engine(url)
    yield eng
    eng.dispose()


@pytest.fixture(autouse=True)
def _clean_tenant_rows(request: pytest.FixtureRequest) -> None:
    if "admin_engine" not in request.fixturenames and "env" not in request.fixturenames:
        return
    eng: Engine = request.getfixturevalue("admin_engine")
    background.wait_idle()  # queued reset work of the previous test (B2-S03)
    with eng.begin() as conn:
        conn.execute(text(f"TRUNCATE {', '.join(TENANT_TABLES)} CASCADE"))
        # Test-only cleanup of reference versions a test published: the immutability
        # triggers (B1-012) are bypassed for this owner-role transaction only.
        conn.execute(text("SET LOCAL session_replication_role = replica"))
        conn.execute(
            text(
                "DELETE FROM rules WHERE rule_pack_id IN (SELECT id FROM rule_packs WHERE code <> 'RP-1')"
            )
        )
        conn.execute(text("ALTER TABLE rule_packs DISABLE TRIGGER rule_packs_immutable"))
        conn.execute(
            text(
                "DELETE FROM publications WHERE object_type = 'rule_pack' AND object_id IN (SELECT id FROM rule_packs WHERE code <> 'RP-1')"
            )
        )
        conn.execute(text("DELETE FROM rule_packs WHERE code <> 'RP-1'"))
        conn.execute(text("ALTER TABLE rule_packs ENABLE TRIGGER rule_packs_immutable"))
        conn.execute(text("DELETE FROM system_flags"))
        conn.execute(text("DELETE FROM auth_attempts"))  # sign-in throttle, per test
        extra_cal = "SELECT id FROM calendar_versions WHERE code NOT IN ('CAL-1', 'CAL-2')"
        conn.execute(text(f"DELETE FROM calendar_rules WHERE calendar_version_id IN ({extra_cal})"))
        conn.execute(text(f"DELETE FROM provisions WHERE calendar_version_id IN ({extra_cal})"))
        conn.execute(text(f"DELETE FROM publications WHERE object_id IN ({extra_cal})"))
        conn.execute(
            text("ALTER TABLE calendar_versions DISABLE TRIGGER calendar_versions_immutable")
        )
        conn.execute(text("DELETE FROM calendar_versions WHERE code NOT IN ('CAL-1', 'CAL-2')"))
        conn.execute(
            text("ALTER TABLE calendar_versions ENABLE TRIGGER calendar_versions_immutable")
        )


@dataclass
class Firm:
    id: uuid.UUID
    tokens: dict[str, str]  # role -> session token (cookie value)
    users: dict[str, uuid.UUID]

    def h(self, role: str = "owner", **extra: str) -> dict[str, str]:
        """Test-only: a seeded full session sent as the session cookie with its
        anti-forgery token, as a signed-in browser would (B2)."""
        tok = self.tokens[role]
        return {"Cookie": f"{SESSION_COOKIE}={tok}", "X-CSRF-Token": csrf_token(tok), **extra}


def make_firm(admin: Engine, name: str) -> Firm:
    fid = uuid.uuid4()
    tokens: dict[str, str] = {}
    users: dict[str, uuid.UUID] = {}
    with admin.begin() as conn:
        conn.execute(
            text("INSERT INTO firms (id, legal_name) VALUES (:i, :n)"), {"i": fid, "n": name}
        )
        for role in ("owner", "reviewer", "preparer"):
            uid = uuid.uuid4()
            tok = secrets.token_urlsafe(32)
            conn.execute(
                text(
                    "INSERT INTO users (id, firm_id, email, role, password_hash, totp_secret_enc) "
                    "VALUES (:i, :f, :e, :r, '!test', '\\x00')"
                ),
                {"i": uid, "f": fid, "e": f"{role}.{fid.hex[:8]}@firm.test", "r": role},
            )
            conn.execute(
                text(
                    "INSERT INTO sessions (firm_id, user_id, token_hash, last_seen_at, "
                    "absolute_expires_at, stage) VALUES (:f, :u, :h, now(), :x, 'full')"
                ),
                {
                    "f": fid,
                    "u": uid,
                    "h": hashlib.sha256(tok.encode()).digest(),
                    "x": datetime.now(tz=UTC) + timedelta(hours=12),
                },
            )
            tokens[role], users[role] = tok, uid
    return Firm(fid, tokens, users)


@dataclass
class Env:
    admin: Engine
    app: Engine
    client: TestClient
    store: ObjectStore
    publisher_id: uuid.UUID
    clock: list[datetime]

    def firm(self, name: str = "Synthetic Bookkeeping FZ-LLC") -> Firm:
        return make_firm(self.admin, name)

    def drain(self, limit: int = 50) -> list[str]:
        out = []
        for _ in range(limit):
            r = run_once(self.app, self.store)
            if r is None:
                break
            out.append(r)
        return out


@pytest.fixture
def env(
    admin_engine: Engine, app_engine: Engine, publisher_id: uuid.UUID, tmp_path: Path
) -> Iterator[Env]:
    store = LocalObjectStore(tmp_path / "storage")
    clock = [datetime.now(tz=UTC)]
    app = create_app(engine=app_engine, store=store, clock=lambda: clock[0])
    with TestClient(app, base_url="https://testserver") as client:
        yield Env(admin_engine, app_engine, client, store, publisher_id, clock)


def upload(
    env: Env,
    firm: Firm,
    entity_id: str,
    dataset: str,
    name: str,
    data: bytes,
    role: str = "preparer",
) -> Any:
    return env.client.post(
        f"/api/v1/entities/{entity_id}/uploads",
        headers=firm.h(role, **{"Idempotency-Key": secrets.token_hex(8)}),
        data={"dataset": dataset},
        files={"file": (name, data)},
    )
