"""Regression tests for review round 1 through the API and worker (B1-001, B1-002, B1-005,
B1-009, the AED 50M boundary, country value mappings, vendor credential grant)."""

from __future__ import annotations

import copy
import uuid
from collections.abc import Sequence

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from pintae_core import readiness, tenancy
from pintae_core.publication import publish_calendar
from pintae_rulepacks import load_data
from pintae_rules.packs import content_hash
from tests.fixtures import synthetic as fx
from tests.integration import flow
from tests.integration.conftest import Env, upload


def test_c1_new_calendar_makes_result_stale_and_rerun_creates_new_run(env: Env) -> None:
    firm = env.firm()
    eid = flow.new_entity(env, firm)
    files = flow.clean_files()
    cust: list[Sequence[object]] = [
        fx.CUSTOMER_HEADERS,
        [
            "C001",
            "Group Member LLC",
            "vat_group_member",
            fx.synthetic_trn(1),
            None,
            "Unit 1",
            "Dubai",
            "AE",
            "DXB",
            "TL",
            "CN-0000001",
            "Dubai DET",
            None,
            None,
        ],
    ]
    inv: list[Sequence[object]] = [
        fx.INVOICE_HEADERS,
        [
            "INV-1",
            "2027-02-01",
            "2027-03-01",
            "380",
            "C001",
            "AED",
            None,
            "30",
            "I001",
            "2000",
            "H87",
            "5.00",
            "10000.00",
            "S",
            "5",
            "10000.00",
            "500.00",
            "99999.00",
            "00000000",
            None,
            None,
        ],
    ]
    files["customers"] = ("customers.csv", fx.csv_bytes(cust))
    files["invoices"] = ("invoices.csv", fx.csv_bytes(inv))
    ids = flow.upload_all(env, firm, eid, files)
    flow.confirm_mappings(env, firm, ids)
    first = flow.run(env, firm, eid)
    rep, res = flow.draft_and_approve(env, firm, eid)
    assert res.status_code == 200 and flow.status(env, firm, eid)["status"] == "data_ready"
    assert rep["pins"]["calendar_version"] == "CAL-2"
    data = copy.deepcopy(load_data("CAL-2"))
    data["code"] = "CAL-3"
    for p in data["provisions"]:
        if p["code"] == "PRV-2":
            p["applies_to"] = "2026-12-31"
    publish_calendar(env.admin, data, env.publisher_id, content_hash(data))
    s = flow.status(env, firm, eid)
    assert s["status"] == "stale" and "calendar_changed" in s["stale_reasons"]
    assert (
        env.client.get(f"/api/v1/reports/{rep['id']}", headers=firm.h()).json()["currency"]
        == "superseded"
    )
    second = flow.run(env, firm, eid)
    assert second["id"] != first["id"]
    s = flow.status(env, firm, eid)
    assert s["status"] == "gaps_open" and s["counts"]["failed_blockers"] >= 1


def test_b1_header_only_invoices_file_never_reaches_data_ready(env: Env) -> None:
    firm = env.firm()
    eid = flow.new_entity(env, firm)
    files = flow.clean_files()
    files["invoices"] = ("invoices.csv", fx.csv_bytes([fx.INVOICE_HEADERS]))
    ids = flow.upload_all(env, firm, eid, files)
    m = env.client.get(f"/api/v1/uploads/{ids['invoices']}/mapping", headers=firm.h()).json()
    assert m["data_rows"] == 0
    flow.confirm_mappings(env, firm, ids)
    flow.run(env, firm, eid)
    s = flow.status(env, firm, eid)
    assert s["status"] == "checks_incomplete" and s["counts"]["empty_datasets"] == ["invoices"]
    _, res = flow.draft_and_approve(env, firm, eid)
    assert res.json()["printed_status"] == "Checks incomplete"
    assert flow.status(env, firm, eid)["status"] == "checks_incomplete"


def test_b1_header_row_set_to_last_row_drops_every_row(env: Env) -> None:
    firm = env.firm()
    eid = flow.new_entity(env, firm)
    ids = flow.upload_all(env, firm, eid, flow.clean_files())
    flow.confirm_mappings(env, firm, {k: v for k, v in ids.items() if k != "invoices"})
    uid = ids["invoices"]
    m = env.client.get(f"/api/v1/uploads/{uid}/mapping", headers=firm.h()).json()
    r = env.client.put(
        f"/api/v1/uploads/{uid}/mapping",
        headers=firm.h("preparer"),
        json={
            "sheet": None,
            "header_row": 4,
            "fields": dict.fromkeys(m["mapping"]["fields"], "absent"),
        },
    )
    assert r.status_code == 200 and r.json()["data_rows"] == 0
    env.client.post(f"/api/v1/uploads/{uid}/mapping/confirm", headers=firm.h("preparer"))
    mid = env.client.get(f"/api/v1/uploads/{uid}/mapping", headers=firm.h()).json()["id"]
    env.client.post(
        f"/api/v1/mappings/{mid}/decision", headers=firm.h("reviewer"), json={"decision": "approve"}
    )
    flow.run(env, firm, eid)
    assert flow.status(env, firm, eid)["status"] == "checks_incomplete"


def test_b3_reupload_is_stale_before_the_worker_parses_it(env: Env) -> None:
    firm = env.firm()
    eid = flow.ready_entity(env, firm)
    _, res = flow.draft_and_approve(env, firm, eid)
    assert res.status_code == 200
    rows: list[Sequence[object]] = [
        fx.INVOICE_HEADERS,
        [
            "INV-9",
            "2026-10-01",
            "2026-10-31",
            "380",
            "C001",
            "AED",
            None,
            "30",
            "I001",
            "1",
            "H87",
            "5.00",
            "5.00",
            "S",
            "5",
            "5.00",
            "0.25",
            "999.00",
            "00000000",
            None,
            None,
        ],
    ]
    r = upload(env, firm, eid, "invoices", "inv2.csv", fx.csv_bytes(rows))
    assert r.status_code == 202  # no worker runs in this test
    s = flow.status(env, firm, eid)
    assert s["status"] == "stale" and "upload_changed" in s["stale_reasons"]
    _, res = flow.draft_and_approve(env, firm, eid)
    assert res.status_code == 409 and res.json()["reason"] == "stale"


def test_rejected_reupload_does_not_change_status(env: Env) -> None:
    firm = env.firm()
    eid = flow.ready_entity(env, firm)
    flow.draft_and_approve(env, firm, eid)
    upload(env, firm, eid, "invoices", "bad.xlsx", fx.fx_e_corrupt())
    env.drain()
    assert flow.status(env, firm, eid)["status"] == "data_ready"


def test_b1_009_approval_holds_the_versions_lock_against_publication(env: Env) -> None:
    firm = env.firm()
    eid = flow.ready_entity(env, firm)
    with tenancy.session(firm.id, env.app) as s:
        readiness.lock_versions_shared(s)
        readiness.lock_entity(s, uuid.UUID(eid))
        with env.admin.connect() as other:
            other.execute(text("SET lock_timeout = '200ms'"))
            with pytest.raises(DBAPIError, match="lock timeout"):
                other.execute(
                    text("SELECT pg_advisory_xact_lock(:k)"), {"k": readiness.VERSIONS_LOCK_KEY}
                )
            other.rollback()
            other.execute(text("SET lock_timeout = '200ms'"))
            with pytest.raises(DBAPIError, match="lock timeout"):
                other.execute(
                    text("UPDATE client_entities SET city = 'x' WHERE id = :i"), {"i": eid}
                )
            other.rollback()


def test_revenue_exactly_50m_shows_ambiguous_segment_with_flag(env: Env) -> None:
    firm = env.firm()
    eid = flow.new_entity(env, firm, revenue_band="eq_50m")
    d = flow.status(env, firm, eid)["deadline"]
    assert d["segment"] == "SEG-U" and d["segment_label"] == "Segment not confirmed"
    assert d["appoint_by"] == "2026-10-30" and d["flags"] == [
        "revenue_exactly_50m_sources_disagree"
    ]


def test_country_value_mapping_kind_is_accepted(env: Env) -> None:
    firm = env.firm()
    eid = flow.new_entity(env, firm)
    r = env.client.put(
        f"/api/v1/entities/{eid}/value-mappings",
        headers=firm.h("preparer"),
        json={"items": [{"kind": "country", "source_value": "Emirates", "target_code": "AE"}]},
    )
    assert r.status_code == 200
    r = env.client.post(
        f"/api/v1/entities/{eid}/value-mappings/decision",
        headers=firm.h("reviewer"),
        json={"items": [{"kind": "country", "source_value": "Emirates"}], "decision": "approve"},
    )
    assert r.status_code == 200 and r.json()["items"][0]["state"] == "approved"


def test_application_role_cannot_read_vendor_credentials(env: Env) -> None:
    with pytest.raises(DBAPIError, match="permission denied"), env.app.connect() as conn:
        conn.execute(text("SELECT password_hash FROM vendor_users"))


# ----------------------------------------------------------------------------- round 2


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE rules SET severity = 'warning' WHERE code = 'RC-17'",
        "DELETE FROM rules WHERE code = 'RC-17'",
        "UPDATE provisions SET applies_to = '2026-12-31' WHERE code = 'PRV-2'",
        "UPDATE calendar_rules SET appoint_by = '2027-12-31' WHERE segment = 'SEG-L'",
        "INSERT INTO rules (rule_pack_id, code, severity, applies_to, source_refs, description) "
        "SELECT id, 'RC-99', 'warning', '{}', '{}', 'x' FROM rule_packs WHERE code = 'RP-1'",
    ],
)
def test_b1_012_published_children_are_immutable_even_for_owner(env: Env, sql: str) -> None:
    with pytest.raises(DBAPIError, match="immutable"), env.admin.begin() as conn:
        conn.execute(text(sql))


def test_b1_012_n5_severity_edit_cannot_produce_data_ready(env: Env) -> None:
    with pytest.raises(DBAPIError), env.admin.begin() as conn:
        conn.execute(text("UPDATE rules SET severity = 'warning' WHERE code = 'RC-17'"))
    firm = env.firm()
    eid = flow.new_entity(env, firm)
    files = flow.clean_files()
    inv: list[Sequence[object]] = [
        fx.INVOICE_HEADERS,
        [
            "INV-1",
            "2026-10-01",
            "2026-10-31",
            "380",
            "C001",
            "AED",
            None,
            "30",
            "I001",
            "2000",
            "H87",
            "5.00",
            "10000.00",
            "S",
            "5",
            "10000.00",
            "500.00",
            "99999.00",
            "00000000",
            None,
            None,
        ],
    ]
    files["invoices"] = ("invoices.csv", fx.csv_bytes(inv))
    ids = flow.upload_all(env, firm, eid, files)
    flow.confirm_mappings(env, firm, ids)
    flow.run(env, firm, eid)
    _, res = flow.draft_and_approve(env, firm, eid)
    assert flow.status(env, firm, eid)["status"] == "gaps_open"
    assert res.json()["printed_status"] == "Gaps open"


def test_b1_010_seg_n_with_past_invoice_dates_is_flagged(env: Env) -> None:
    firm = env.firm()
    r = env.client.post("/api/v1/entities", headers=firm.h(), json={"legal_name": "New Co"})
    eid = r.json()["id"]
    env.client.patch(f"/api/v1/entities/{eid}", headers=firm.h(), json=flow.CLEAN_PROFILE)
    seg = env.client.post(
        f"/api/v1/entities/{eid}/segment-assessments",
        headers=firm.h(),
        json={
            "entity_type": "person",
            "revenue_band": "lt_50m",
            "newly_established": True,
            "first_invoice_state": "not_yet",
        },
    ).json()
    env.client.post(
        f"/api/v1/segment-assessments/{seg['id']}/decision",
        headers=firm.h("reviewer"),
        json={"decision": "approve"},
    )
    assert flow.status(env, firm, eid)["deadline"]["display"] == "Before first invoice"
    ids = flow.upload_all(env, firm, eid, flow.clean_files())  # invoices dated 2026-10-01
    flow.confirm_mappings(env, firm, ids)
    flow.run(env, firm, eid)
    d = flow.status(env, firm, eid)["deadline"]
    assert d["appoint_by_passed"] is True and d["flags"] == ["invoices_dated_before_today"]
