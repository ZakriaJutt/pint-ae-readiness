"""B1-014 and B1-015 regressions: calendars published before migration 0004 have no stored
content.

The migration step (0004b) fills it once, only with the calendar file shipped for that code
and only when the stored rows are identical to it (B1-015); any other version becomes
``legacy_unverified``: never newly pinned, pinned results read
Stale with a reason, and no read or run returns 500. The upgrade from the pushed 0003 schema
itself is exercised by the reviewer's round-4 upgrade script and on ``pintae_dev``.
"""

from __future__ import annotations

import copy

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.orm import Session

from pintae_api.main import readiness_checks
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


def test_backfill_untouched_calendar_matching_the_shipped_file_is_verified(env: Env) -> None:
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


CAL2 = "(SELECT id FROM calendar_versions WHERE code = 'CAL-2')"


@pytest.mark.parametrize(
    "label,table,sql",
    [
        # The reviewer's U6a: SEG-S appoint-by moved from 2027-03-31 to 2028-12-31 at 0003.
        ("SEG-S deadline moved", "calendar_rules",
         f"UPDATE calendar_rules SET appoint_by = '2028-12-31' WHERE calendar_version_id = {CAL2}"
         " AND segment = 'SEG-S'"),
        # U6c: the grace provisions dropped.
        ("provisions deleted", "provisions",
         f"DELETE FROM provisions WHERE calendar_version_id = {CAL2}"),
        ("a note edited", "calendar_rules",
         f"UPDATE calendar_rules SET note = 'seeded by older code' WHERE calendar_version_id = "
         f"{CAL2} AND segment = 'SEG-L'"),
        ("stored hash changed", "calendar_versions",
         "UPDATE calendar_versions SET content_hash = '\\x00' WHERE code = 'CAL-2'"),
    ],
)  # fmt: skip
def test_b1_015_rows_edited_before_the_upgrade_are_never_verified(
    env: Env, label: str, table: str, sql: str
) -> None:
    """The database's own rows cannot vouch for themselves: only content identical to the
    shipped definition of the code is verified; anything else is legacy_unverified."""
    with env.admin.connect() as conn:
        tx = conn.begin()
        try:
            _as_before_0004(conn, "CAL-2")
            conn.execute(text(f"ALTER TABLE {table} DISABLE TRIGGER USER"))
            conn.execute(text(sql))
            conn.execute(text(f"ALTER TABLE {table} ENABLE TRIGGER USER"))
            conn.execute(
                text("ALTER TABLE calendar_versions DISABLE TRIGGER calendar_versions_immutable")
            )
            assert _derive(conn) == {"CAL-2": "legacy_unverified"}, label
            content, _, origin = _row(conn, "CAL-2")
            assert content is None and origin == "legacy_unverified"
            s = Session(bind=conn)
            with pytest.raises(readiness.DomainError) as exc:
                readiness.calendar_by_code(s, "CAL-2")
            assert exc.value.code == 409 and exc.value.reason == "calendar_legacy_unverified"
            assert readiness.current_calendar(s).code == "CAL-1"  # never newly pinned
            assert readiness.newest_calendar_unverified(s) == "CAL-2"  # operator signal
        finally:
            tx.rollback()


def test_b1_015_rows_backfilled_by_the_earlier_draft_are_read_as_unverified(env: Env) -> None:
    """A database upgraded with the round-4 draft holds ``derived_from_rows``: not served."""
    with env.admin.connect() as conn:
        tx = conn.begin()
        try:
            conn.execute(
                text("ALTER TABLE calendar_versions DISABLE TRIGGER calendar_versions_immutable")
            )
            conn.execute(
                text(
                    "UPDATE calendar_versions SET content_origin = 'derived_from_rows'"
                    " WHERE code = 'CAL-2'"
                )
            )
            s = Session(bind=conn)
            with pytest.raises(readiness.DomainError) as exc:
                readiness.calendar_by_code(s, "CAL-2")
            assert exc.value.code == 409
            assert readiness.current_calendar(s).code == "CAL-1"
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
    assert (
        "newest_calendar_unverified:CAL-3" in readiness_checks(env.app, env.store)["reference_data"]
    )
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
