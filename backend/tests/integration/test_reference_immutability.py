"""B1-012 round 3 regressions (reviewer cases X3-X6): published reference data is frozen.

Every statement here runs as the owner role, the role that runs migrations and publication,
with no trigger disabled, inside a transaction that is rolled back whatever happens, so that
RP-1, CAL-1 and CAL-2 stay intact for the rest of the suite.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping, Sequence

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from pintae_api.main import readiness_checks
from pintae_core import readiness
from pintae_core.models import CalendarVersion, RulePackRow
from pintae_core.publication import PublicationRefused, publish_rule_pack, withdraw
from pintae_rulepacks import load_data
from pintae_rules.packs import content_hash
from tests.fixtures import synthetic as fx
from tests.helpers import rp1_cases
from tests.integration import flow
from tests.integration.conftest import Env

GUARDED = (
    "rule_packs",
    "rules",
    "calendar_versions",
    "calendar_rules",
    "provisions",
    "publications",
)


class _Rollback(Exception):
    pass


def _attempt(engine: Engine, statements: Sequence[tuple[str, Mapping[str, object]]]) -> str:
    """Run the statements in one transaction that is always rolled back."""
    try:
        with engine.begin() as conn:
            for sql, params in statements:
                conn.execute(text(sql), params)
            raise _Rollback
    except _Rollback:
        return "accepted"
    except DBAPIError as exc:
        return "refused: " + str(exc.orig).splitlines()[0]


def _rp1_content(env: Env) -> dict[str, object]:
    with env.admin.connect() as conn:
        return dict(
            conn.execute(text("SELECT content FROM rule_packs WHERE code = 'RP-1'")).scalar_one()
        )


def _wrong_total_files() -> dict[str, tuple[str, bytes]]:
    files = flow.clean_files()
    inv: list[Sequence[object]] = [
        fx.INVOICE_HEADERS,
        ["INV-1", "2026-10-01", "2026-10-31", "380", "C001", "AED", None, "30", "I001", "2000",
         "H87", "5.00", "10000.00", "S", "5", "10000.00", "500.00", "99999.00", "00000000",
         None, None],
    ]  # fmt: skip
    files["invoices"] = ("invoices.csv", fx.csv_bytes(inv))
    return files


# ----------------------------------------------------------------------------- X6


def test_x6_withdraw_edit_republish_is_refused_and_wrong_total_is_not_data_ready(
    env: Env,
) -> None:
    edited = copy.deepcopy(_rp1_content(env))
    for r in edited["rules"]:  # type: ignore[attr-defined]
        if r["code"] == "RC-17":
            r["severity"] = "warning"
    Step = tuple[str, Mapping[str, object]]
    withdraw_sql: Step = ("UPDATE rule_packs SET status = 'withdrawn' WHERE code = 'RP-1'", {})
    edit_sql: Step = (
        "UPDATE rule_packs SET content = CAST(:c AS jsonb) WHERE code = 'RP-1'",
        {"c": json.dumps(edited)},
    )
    republish_sql: Step = ("UPDATE rule_packs SET status = 'published' WHERE code = 'RP-1'", {})
    to_draft_sql: Step = ("UPDATE rule_packs SET status = 'draft' WHERE code = 'RP-1'", {})
    # The reviewer's sequence, and each step that follows a withdrawal on its own.
    assert "immutable" in _attempt(env.admin, [withdraw_sql, edit_sql, republish_sql])
    assert "immutable" in _attempt(env.admin, [withdraw_sql, republish_sql])
    assert "immutable" in _attempt(env.admin, [withdraw_sql, to_draft_sql])
    assert "immutable" in _attempt(env.admin, [to_draft_sql])
    assert "immutable" in _attempt(env.admin, [edit_sql])
    for col, val in (("content_hash", "'\\x00'"), ("created_at", "now()"),
                     ("published_at", "now()"), ("effective_from", "'2030-01-01'")):  # fmt: skip
        out = _attempt(
            env.admin,
            [withdraw_sql, (f"UPDATE rule_packs SET {col} = {val} WHERE code = 'RP-1'", {})],
        )
        assert "immutable" in out, (col, out)
    assert _rp1_content(env) != edited
    # The invoice with a wrong total stays Gaps open under the untouched RP-1.
    firm = env.firm()
    eid = flow.new_entity(env, firm)
    ids = flow.upload_all(env, firm, eid, _wrong_total_files())
    flow.confirm_mappings(env, firm, ids)
    flow.run(env, firm, eid)
    _, res = flow.draft_and_approve(env, firm, eid)
    assert flow.status(env, firm, eid)["status"] == "gaps_open"
    assert res.json()["printed_status"] == "Gaps open"


# ----------------------------------------------------------------------------- X5, X4


def test_x5_calendar_status_flip_cannot_unlock_children(env: Env) -> None:
    cal2 = "(SELECT id FROM calendar_versions WHERE code = 'CAL-2')"
    steps: list[tuple[str, Mapping[str, object]]] = [
        ("UPDATE calendar_versions SET status = 'withdrawn' WHERE code = 'CAL-2'", {}),
        ("UPDATE calendar_versions SET status = 'draft' WHERE code = 'CAL-2'", {}),
        (
            f"UPDATE calendar_rules SET appoint_by = '2028-12-31' WHERE calendar_version_id = {cal2}",
            {},
        ),
        (f"DELETE FROM provisions WHERE calendar_version_id = {cal2}", {}),
        ("UPDATE calendar_versions SET status = 'published' WHERE code = 'CAL-2'", {}),
    ]
    assert "immutable" in _attempt(env.admin, steps)
    # After a withdrawal alone, the children are still frozen.
    for child in steps[2:4]:
        assert "immutable" in _attempt(env.admin, [steps[0], child])


def test_x4_child_row_cannot_be_moved_to_a_draft_parent(env: Env) -> None:
    out = _attempt(
        env.admin,
        [
            (
                "INSERT INTO rule_packs (code, basis, released_on, effective_from, effective_label,"
                " status, content_hash, content) SELECT 'RP-X', basis, released_on, effective_from,"
                " effective_label, 'draft', content_hash, content FROM rule_packs WHERE code = 'RP-1'",
                {},
            ),
            (
                "UPDATE rules SET rule_pack_id = (SELECT id FROM rule_packs WHERE code = 'RP-X')"
                " WHERE code = 'RC-17' AND rule_pack_id ="
                " (SELECT id FROM rule_packs WHERE code = 'RP-1')",
                {},
            ),
        ],
    )
    assert "immutable" in out


def test_draft_cannot_become_published_by_update(env: Env) -> None:
    out = _attempt(
        env.admin,
        [
            (
                "INSERT INTO rule_packs (code, basis, released_on, effective_from, effective_label,"
                " status, content_hash, content) SELECT 'RP-X', basis, released_on, effective_from,"
                " effective_label, 'draft', content_hash, content FROM rule_packs WHERE code = 'RP-1'",
                {},
            ),
            ("UPDATE rule_packs SET status = 'published' WHERE code = 'RP-X'", {}),
        ],
    )
    assert "publication path" in out


# ----------------------------------------------------------------------------- X3 and privileges


@pytest.mark.parametrize("table", GUARDED)
@pytest.mark.parametrize("cascade", ["", " CASCADE"])
def test_x3_truncate_refused_for_owner_and_app_role(env: Env, table: str, cascade: str) -> None:
    owner = _attempt(env.admin, [(f"TRUNCATE {table}{cascade}", {})])
    # Without CASCADE a referenced table is already refused by its foreign keys; with
    # CASCADE (the reviewer's X3 form) the statement trigger refuses.
    allowed = ("TRUNCATE is refused",) if cascade else ("TRUNCATE is refused", "foreign key")
    assert owner.startswith("refused") and any(a in owner for a in allowed), owner
    app = _attempt(env.app, [(f"TRUNCATE {table}{cascade}", {})])
    assert "permission denied" in app, app


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE publications SET fixture_run_ref = 'x'",
        "DELETE FROM publications",
        "DELETE FROM rule_packs WHERE code = 'RP-1'",
        "DELETE FROM calendar_versions WHERE code = 'CAL-2'",
    ],
)
def test_publication_records_and_parents_cannot_be_deleted_or_edited(env: Env, sql: str) -> None:
    out = _attempt(env.admin, [(sql, {})])
    assert "immutable" in out or "cannot be deleted" in out, out


def test_privileges_revoked_for_app_role_public_and_owner(env: Env) -> None:
    with env.admin.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT grantee, table_name, privilege_type FROM information_schema.role_table_grants"
                " WHERE table_name = ANY(:t) AND privilege_type IN ('UPDATE', 'DELETE', 'TRUNCATE')"
            ),
            {"t": list(GUARDED)},
        ).all()
        cols = conn.execute(
            text(
                "SELECT grantee, table_name, column_name FROM information_schema.column_privileges"
                " WHERE table_name = ANY(:t) AND privilege_type = 'UPDATE'"
            ),
            {"t": list(GUARDED)},
        ).all()
        owner = conn.execute(text("SELECT current_user")).scalar_one()
    assert rows == []  # no role holds table-level UPDATE, DELETE or TRUNCATE
    assert {(g, t, c) for g, t, c in cols} == {
        (owner, "rule_packs", "status"),
        (owner, "calendar_versions", "status"),
    }


# ----------------------------------------------------------------------------- withdrawal, pins


def test_withdrawal_is_terminal_and_pinned_runs_stay_pinned(env: Env) -> None:
    data = load_data("RP-1")
    data["code"], data["released_on"] = "RP-2", "2026-11-01"
    publish_rule_pack(env.admin, data, rp1_cases(), env.publisher_id, content_hash(data))
    firm = env.firm()
    eid = flow.ready_entity(env, firm)
    assert flow.status(env, firm, eid)["status"] == "review_pending"
    pack_id = withdraw(env.admin, "rule_pack", "RP-2", env.publisher_id)
    # The run stays pinned to RP-2; the result is Stale because RP-1 is now in force.
    with Session(env.admin) as s:
        run = s.execute(
            text("SELECT rule_pack_id FROM check_runs WHERE entity_id = :e"), {"e": eid}
        ).scalar_one()
        assert run == pack_id
        row = s.get(RulePackRow, pack_id)
        assert row is not None and row.status == "withdrawn"
        assert readiness.load_pack(row).code == "RP-2"  # the pinned content still loads
    assert flow.status(env, firm, eid)["status"] == "stale"
    _, res = flow.draft_and_approve(env, firm, eid)
    assert res.status_code == 409
    # Terminal: not republished by the publication path, nor by UPDATE, nor withdrawn twice.
    with pytest.raises(PublicationRefused) as exc:
        publish_rule_pack(env.admin, data, rp1_cases(), env.publisher_id, content_hash(data))
    assert exc.value.reason == "version_withdrawn"
    with pytest.raises(PublicationRefused) as exc:
        withdraw(env.admin, "rule_pack", "RP-2", env.publisher_id)
    assert exc.value.reason == "not_published"
    out = _attempt(
        env.admin, [("UPDATE rule_packs SET status = 'published' WHERE code = 'RP-2'", {})]
    )
    assert "terminal" in out


# ----------------------------------------------------------------------------- content hash


def _tampered(env: Env, statements: Sequence[str], table: str) -> readiness.DomainError:
    """Tamper with the triggers disabled (test only), inside a rolled-back transaction, and
    return what the loader says."""
    with env.admin.connect() as conn:
        tx = conn.begin()
        try:
            conn.execute(text(f"ALTER TABLE {table} DISABLE TRIGGER USER"))
            for sql in statements:
                conn.execute(text(sql))
            s = Session(bind=conn)
            with pytest.raises(readiness.DomainError) as exc:
                if table == "rule_packs":
                    row = s.execute(
                        text("SELECT id FROM rule_packs WHERE code = 'RP-1'")
                    ).scalar_one()
                    pack = s.get(RulePackRow, row)
                    assert pack is not None
                    readiness.load_pack(pack)
                else:
                    readiness.calendar_by_code(s, "CAL-2")
            s.close()
            return exc.value
        finally:
            tx.rollback()


def test_loaders_refuse_content_that_does_not_match_its_hash(env: Env) -> None:
    err = _tampered(
        env,
        [
            "UPDATE rule_packs SET content = jsonb_set(content, '{basis}', '\"edited\"')"
            " WHERE code = 'RP-1'"
        ],
        "rule_packs",
    )
    assert err.reason == "rule_pack_content_hash_mismatch"
    err = _tampered(
        env,
        [
            "UPDATE calendar_versions SET content = jsonb_set(content, '{basis}', '\"edited\"')"
            " WHERE code = 'CAL-2'"
        ],
        "calendar_versions",
    )
    assert err.reason == "calendar_content_hash_mismatch"
    err = _tampered(
        env,
        [
            "UPDATE calendar_rules SET appoint_by = '2028-12-31' WHERE calendar_version_id ="
            " (SELECT id FROM calendar_versions WHERE code = 'CAL-2')"
        ],
        "calendar_rules",
    )
    assert err.reason == "calendar_rows_differ_from_content"
    with Session(env.admin) as s:  # untouched versions load
        assert readiness.calendar_by_code(s, "CAL-2").code == "CAL-2"
        cal_row = s.query(CalendarVersion).filter_by(code="CAL-2").one()
        assert cal_row.content is not None


def test_readiness_check_verifies_reference_data(env: Env) -> None:
    checks = readiness_checks(env.app, env.store)
    assert checks["reference_data"] == "ok", checks
