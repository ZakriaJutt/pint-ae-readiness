"""B1-014 regressions: calendars published before migration 0004 have no stored content.

The migration step (0004b) fills it once from the version's own rows; a version whose rows
cannot be verified becomes ``legacy_unverified``: never newly pinned, pinned results read
Stale with a reason, and no read or run returns 500. The upgrade from the pushed 0003 schema
itself is exercised by the reviewer's round-4 upgrade script and on ``pintae_dev``.
"""

from __future__ import annotations

import copy

from sqlalchemy import Connection, text
from sqlalchemy.orm import Session

from pintae_core import readiness
from pintae_core.calendar_content import derive_missing_content
from pintae_core.publication import publish_calendar
from pintae_rulepacks import load_data
from pintae_rules.packs import content_hash
from tests.integration import flow
from tests.integration.conftest import Env

UNSET = "UPDATE calendar_versions SET content = NULL, content_origin = NULL WHERE code = :c"


def _as_before_0004(conn: Connection, code: str) -> None:
    """Test only: put a version back in the state migration 0004 left it in."""
    conn.execute(text("ALTER TABLE calendar_versions DISABLE TRIGGER calendar_versions_immutable"))
    conn.execute(text(UNSET), {"c": code})


def _derive(conn: Connection) -> dict[str, str]:
    out = derive_missing_content(conn)
    conn.execute(text("ALTER TABLE calendar_versions ENABLE TRIGGER calendar_versions_immutable"))
    return out


def _row(conn: Connection, code: str) -> tuple[object, ...]:
    r = conn.execute(
        text("SELECT content, content_hash, content_origin FROM calendar_versions WHERE code = :c"),
        {"c": code},
    ).one()
    return tuple(r)


def test_backfill_uses_the_published_file_when_it_matches_hash_and_rows(env: Env) -> None:
    with env.admin.connect() as conn:
        tx = conn.begin()
        try:
            _, before_hash, _ = _row(conn, "CAL-2")
            _as_before_0004(conn, "CAL-2")
            assert _derive(conn) == {"CAL-2": "publication"}
            content, digest, origin = _row(conn, "CAL-2")
            assert origin == "publication" and digest == before_hash
            assert content == load_data("CAL-2")
            assert readiness.calendar_by_code(Session(bind=conn), "CAL-2").code == "CAL-2"
            assert derive_missing_content(conn) == {}  # idempotent: nothing left to fill
        finally:
            tx.rollback()


def test_backfill_derives_content_from_rows_when_the_file_differs(env: Env) -> None:
    with env.admin.connect() as conn:
        tx = conn.begin()
        try:
            _as_before_0004(conn, "CAL-2")
            # Rows that no shipped file describes (as on a database seeded by older code).
            conn.execute(text("ALTER TABLE calendar_rules DISABLE TRIGGER USER"))
            conn.execute(
                text(
                    "UPDATE calendar_rules SET note = 'seeded by older code' WHERE "
                    "calendar_version_id = (SELECT id FROM calendar_versions WHERE code = 'CAL-2')"
                    " AND segment = 'SEG-L'"
                )
            )
            conn.execute(text("ALTER TABLE calendar_rules ENABLE TRIGGER USER"))
            assert _derive(conn) == {"CAL-2": "derived_from_rows"}
            content, digest, _ = _row(conn, "CAL-2")
            assert isinstance(content, dict) and digest == content_hash(content)
            cal = readiness.calendar_by_code(Session(bind=conn), "CAL-2")
            assert cal.rule("SEG-L").note == "seeded by older code"
            # Frozen again afterwards: the derived content cannot be edited.
            out = None
            try:
                with conn.begin_nested():
                    conn.execute(
                        text("UPDATE calendar_versions SET content = '{}' WHERE code = 'CAL-2'")
                    )
            except Exception as exc:
                out = str(exc)
            assert out is not None and "immutable" in out
        finally:
            tx.rollback()


def test_unverifiable_calendar_is_legacy_never_pinned_and_pinned_results_read_stale(
    env: Env,
) -> None:
    data = copy.deepcopy(load_data("CAL-2"))
    data["code"] = "CAL-3"
    publish_calendar(env.admin, data, env.publisher_id, content_hash(data))
    firm = env.firm()
    eid = flow.ready_entity(env, firm)
    assert flow.status(env, firm, eid)["status"] == "review_pending"
    # CAL-3 loses its content and its rows no longer form a calendar (committed; test only).
    with env.admin.begin() as conn:
        _as_before_0004(conn, "CAL-3")
        conn.execute(text("ALTER TABLE calendar_rules DISABLE TRIGGER USER"))
        conn.execute(
            text(
                "DELETE FROM calendar_rules WHERE calendar_version_id ="
                " (SELECT id FROM calendar_versions WHERE code = 'CAL-3')"
            )
        )
        conn.execute(text("ALTER TABLE calendar_rules ENABLE TRIGGER USER"))
        assert _derive(conn) == {"CAL-3": "legacy_unverified"}
    c = env.client
    r = c.get(f"/api/v1/entities/{eid}", headers=firm.h())
    assert r.status_code == 200, r.text
    s = flow.status(env, firm, eid)
    assert s["status"] == "stale" and s["stale_reasons"][0] == "calendar_legacy_unverified"
    assert c.get("/api/v1/dashboard", headers=firm.h()).status_code == 200
    assert c.get("/api/v1/calendar-versions", headers=firm.h()).status_code == 200
    _, res = flow.draft_and_approve(env, firm, eid)
    assert res.status_code == 409
    # A new run pins the newest verified calendar, never the legacy one.
    run = flow.run(env, firm, eid)
    with env.admin.connect() as conn:
        pinned = conn.execute(
            text("SELECT inputs->>'calendar_version' FROM check_runs WHERE id = :i"),
            {"i": run["id"]},
        ).scalar_one()
    assert pinned == "CAL-2"
    assert "calendar_legacy_unverified" not in flow.status(env, firm, eid)["stale_reasons"]
