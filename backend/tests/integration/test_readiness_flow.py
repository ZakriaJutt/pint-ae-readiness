"""Core path through API and worker: upload, map, run, status, report approval.

Covers UT-11 rows through the real entry points (R-03), E2E-02 (a)-(c) at API level,
IT-07, IT-12, IT-13, IT-17 (derivation parts) and UT-17 on read.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import timedelta

import pytest

from pintae_core.publication import PublicationRefused, publish_rule_pack
from pintae_rulepacks import load_data
from pintae_rules.packs import content_hash
from tests.helpers import rp1_cases
from tests.integration import flow
from tests.integration.conftest import Env


def publish_rp2(env: Env) -> None:
    data = load_data("RP-1")
    data["code"], data["released_on"] = "RP-2", "2026-11-01"
    publish_rule_pack(env.admin, data, rp1_cases(), env.publisher_id, content_hash(data))


def test_clean_entity_reaches_data_ready_only_after_review(env: Env) -> None:
    firm = env.firm()
    eid = flow.ready_entity(env, firm)
    s = flow.status(env, firm, eid)
    assert s["status"] == "review_pending", s
    assert s["counts"]["failed_blockers"] == 0 and s["counts"]["unchecked_blockers"] == 0
    rep, res = flow.draft_and_approve(env, firm, eid)
    assert rep["watermark"] == "DRAFT"
    assert res.status_code == 200, res.text
    assert res.json()["printed_status"] == "Data-ready (RP-1)"
    s = flow.status(env, firm, eid)
    assert s["status"] == "data_ready" and s["label"] == "Data-ready (RP-1)"
    # UT-17 on read, no job running: 45 days later still Data-ready, 46 days later Stale.
    base = env.clock[0]
    env.clock[0] = base + timedelta(days=45)
    assert flow.status(env, firm, eid)["status"] == "data_ready"
    env.clock[0] = base + timedelta(days=46)
    s = flow.status(env, firm, eid)
    assert s["status"] == "stale" and s["stale_reasons"] == ["data_older_than_45_days"]


def test_unapproved_mapping_blocks_approval(env: Env) -> None:
    firm = env.firm()
    eid = flow.new_entity(env, firm)
    ids = flow.upload_all(env, firm, eid, flow.clean_files())
    flow.confirm_mappings(env, firm, ids, approve=False)
    flow.run(env, firm, eid)
    assert flow.status(env, firm, eid)["status"] == "review_pending"
    _, res = flow.draft_and_approve(env, firm, eid)
    assert res.status_code == 409 and res.json()["reason"] == "mappings_not_approved"


def test_e2e02_false_ready_paths_at_api_level(env: Env) -> None:
    firm = env.firm()
    eid = flow.new_entity(env, firm)
    files = flow.clean_files()
    ids = flow.upload_all(env, firm, eid, files)
    # (b) buyer TRN and TIN marked "not in this file": Checks incomplete, never Data-ready.
    flow.confirm_mappings(env, firm, ids, absent={"customers": ["trn", "tin"]})
    flow.run(env, firm, eid)
    s = flow.status(env, firm, eid)
    assert s["status"] == "checks_incomplete", s
    assert s["counts"]["score_by_dataset"]["customers"]["score_percent"] == "0.0"
    _, res = flow.draft_and_approve(env, firm, eid)
    assert res.status_code == 200
    assert res.json()["printed_status"] == "Checks incomplete"
    assert flow.status(env, firm, eid)["status"] == "checks_incomplete"


def test_accepted_exception_is_exceptions_open_and_other_checks_still_run(env: Env) -> None:
    firm = env.firm()
    eid = flow.new_entity(env, firm)
    files = flow.clean_files()
    from tests.fixtures import synthetic as fx

    rows: list[list[object]] = [
        fx.CUSTOMER_HEADERS,
        [
            "C001",
            "Buyer",
            "uae_business",
            None,
            None,
            "Unit 1",
            "Dubai",
            "AE",
            "DUB",
            "TL",
            "CN-1",
            "Dubai DET",
            None,
            None,
        ],
    ]
    files["customers"] = ("customers.csv", fx.csv_bytes(rows))
    ids = flow.upload_all(env, firm, eid, files)
    flow.confirm_mappings(env, firm, ids)
    flow.run(env, firm, eid)
    findings = env.client.get(f"/api/v1/entities/{eid}/findings", headers=firm.h()).json()["items"]
    rc07 = next(f for f in findings if f["rule"] == "RC-07")
    assert any(f["rule"] == "RC-06" and f["column"] == "Emirate" for f in findings)  # UT-14
    ex = env.client.post(
        f"/api/v1/findings/{rc07['id']}/exceptions",
        headers=firm.h("preparer"),
        json={"reason": "Buyer is registering; client to supply TRN"},
    ).json()
    r = env.client.post(
        f"/api/v1/exceptions/{ex['id']}/decision",
        headers=firm.h("reviewer"),
        json={"decision": "accept"},
    )
    assert r.status_code == 200
    s = flow.status(env, firm, eid)
    assert s["status"] == "gaps_open"  # the emirate failure still stands
    assert s["counts"]["accepted_exceptions"] == 1


def test_exception_on_not_checked_is_refused(env: Env) -> None:
    firm = env.firm()
    eid = flow.new_entity(env, firm)
    ids = flow.upload_all(env, firm, eid, flow.clean_files())
    flow.confirm_mappings(env, firm, ids, absent={"customers": ["trn", "tin"]})
    flow.run(env, firm, eid)
    f = next(
        x
        for x in env.client.get(f"/api/v1/entities/{eid}/findings", headers=firm.h()).json()[
            "items"
        ]
        if x["outcome"] == "not_checked"
    )
    r = env.client.post(
        f"/api/v1/findings/{f['id']}/exceptions", headers=firm.h(), json={"reason": "try it"}
    )
    assert r.status_code == 409


def test_self_billed_records_need_reviewer_resolution(env: Env) -> None:
    firm = env.firm()
    eid = flow.new_entity(env, firm)
    files = flow.clean_files()
    from tests.fixtures import synthetic as fx

    inv: list[Sequence[object]] = [
        fx.INVOICE_HEADERS,
        *[
            [
                n,
                "2026-10-01",
                "2026-10-31",
                t,
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
                "10500.00",
                "00000000",
                None,
                None,
            ]
            for n, t in (("INV-1", "380"), ("SB-1", "389"), ("SB-2", "389"))
        ],
    ]
    files["invoices"] = ("invoices.csv", fx.csv_bytes(inv))
    ids = flow.upload_all(env, firm, eid, files)
    flow.confirm_mappings(env, firm, ids)
    flow.run(env, firm, eid)
    s = flow.status(env, firm, eid)
    assert s["status"] == "checks_incomplete" and s["counts"]["unresolved_manual_reviews"] == 2
    mr = [
        f["id"]
        for f in env.client.get(f"/api/v1/entities/{eid}/findings", headers=firm.h()).json()[
            "items"
        ]
        if f["outcome"] == "manual_review"
    ]
    r = env.client.post(
        "/api/v1/findings/review-resolutions",
        headers=firm.h("preparer"),
        json={"finding_ids": mr, "resolution": "confirmed_self_billed"},
    )
    assert r.status_code == 403
    r = env.client.post(
        "/api/v1/findings/review-resolutions",
        headers=firm.h("reviewer"),
        json={"finding_ids": mr, "resolution": "confirmed_self_billed"},
    )
    assert r.status_code == 200
    s = flow.status(env, firm, eid)
    assert s["status"] == "review_pending" and s["counts"]["not_assessed_self_billed"] == 2


def test_it07_it17_new_pack_between_run_and_approval(env: Env) -> None:
    firm = env.firm()
    eid = flow.ready_entity(env, firm)
    approved, res = flow.draft_and_approve(env, firm, eid)
    assert res.status_code == 200
    draft = env.client.post(f"/api/v1/entities/{eid}/reports", headers=firm.h()).json()
    publish_rp2(env)  # no notify_stale job exists or runs: staleness is derived on read
    s = flow.status(env, firm, eid)
    assert s["status"] == "stale" and "rule_pack_changed" in s["stale_reasons"]
    looked = env.client.get(
        f"/api/v1/reports/lookup?code={approved['reference_code']}", headers=firm.h()
    ).json()
    assert looked["currency"] == "superseded"
    r = env.client.post(
        f"/api/v1/reports/{draft['id']}/approve",
        headers=firm.h("reviewer"),
        json={"pins": draft["pins"]},
    )
    assert r.status_code == 409 and r.json()["reason"] == "stale"
    assert r.json()["current_versions"]["rule_pack"] == "RP-2"
    flow.run(env, firm, eid)
    _rep, res = flow.draft_and_approve(env, firm, eid)
    assert res.status_code == 200 and res.json()["printed_status"] == "Data-ready (RP-2)"
    assert (
        env.client.get(f"/api/v1/reports/{approved['id']}", headers=firm.h()).json()["currency"]
        == "superseded"
    )


def test_it12_publication_refusals(env: Env) -> None:
    firm = env.firm()
    eid = flow.ready_entity(env, firm)
    bad = load_data("RP-1")
    bad["code"], bad["released_on"] = "RP-2", "2026-11-01"
    bad["patterns"]["trn"] = "^[0-9]{15}$"  # would pass TRNs ending 01: fixture suite catches it
    with pytest.raises(PublicationRefused) as exc:
        publish_rule_pack(env.admin, bad, rp1_cases(), env.publisher_id, content_hash(bad))
    assert exc.value.reason == "fixture_suite_failed"
    changed = load_data("RP-1")
    changed["basis"] += " (edited)"
    with pytest.raises(PublicationRefused) as exc:
        publish_rule_pack(env.admin, changed, rp1_cases(), env.publisher_id, content_hash(changed))
    assert exc.value.reason == "content_changed_under_existing_code"
    good = load_data("RP-1")
    good["code"], good["released_on"] = "RP-2", "2026-11-01"
    with pytest.raises(PublicationRefused) as exc:
        publish_rule_pack(env.admin, good, rp1_cases(), env.publisher_id, b"\x00" * 32)
    assert exc.value.reason == "confirmed_hash_differs_from_fixture_run"
    assert flow.status(env, firm, eid)["status"] == "review_pending"
    publish_rp2(env)
    assert flow.status(env, firm, eid)["status"] == "stale"


def test_it13_segment_change_moves_dates_and_supersedes(env: Env) -> None:
    firm = env.firm()
    eid = flow.ready_entity(env, firm)
    approved, res = flow.draft_and_approve(env, firm, eid)
    assert res.status_code == 200
    before = flow.status(env, firm, eid)["deadline"]
    assert before["segment"] == "SEG-S" and before["appoint_by"] == "2027-03-31"
    r = env.client.post(
        f"/api/v1/entities/{eid}/segment-assessments",
        headers=firm.h("preparer"),
        json={"entity_type": "person", "revenue_band": "ge_50m"},
    )
    # A proposal changes nothing until a Reviewer approves it.
    assert flow.status(env, firm, eid)["deadline"]["segment"] == "SEG-S"
    env.client.post(
        f"/api/v1/segment-assessments/{r.json()['id']}/decision",
        headers=firm.h("reviewer"),
        json={"decision": "approve"},
    )
    s = flow.status(env, firm, eid)
    assert s["deadline"]["segment"] == "SEG-L" and s["deadline"]["appoint_by"] == "2026-10-30"
    assert s["status"] == "stale" and "segment_changed" in s["stale_reasons"]
    assert (
        env.client.get(f"/api/v1/reports/{approved['id']}", headers=firm.h()).json()["currency"]
        == "superseded"
    )


def test_unknown_revenue_shows_segment_not_confirmed_with_both_outcomes(env: Env) -> None:
    firm = env.firm()
    eid = flow.new_entity(env, firm, revenue_band="unknown")
    s = flow.status(env, firm, eid)
    assert s["status"] == "not_started"
    ids = flow.upload_all(env, firm, eid, flow.clean_files())
    flow.confirm_mappings(env, firm, ids)
    flow.run(env, firm, eid)
    s = flow.status(env, firm, eid)
    assert s["status"] == "segment_not_confirmed"
    assert {o["segment"] for o in s["deadline"]["outcomes"]} == {"SEG-L", "SEG-S"}
    assert s["deadline"]["appoint_by"] == "2026-10-30"


def test_missing_dataset_is_data_incomplete(env: Env) -> None:
    firm = env.firm()
    eid = flow.new_entity(env, firm)
    files = flow.clean_files()
    del files["invoices"]
    ids = flow.upload_all(env, firm, eid, files)
    flow.confirm_mappings(env, firm, ids)
    flow.run(env, firm, eid)
    assert flow.status(env, firm, eid)["status"] == "data_incomplete"


def test_profile_change_makes_result_stale(env: Env) -> None:
    firm = env.firm()
    eid = flow.ready_entity(env, firm)
    env.client.patch(f"/api/v1/entities/{eid}", headers=firm.h(), json={"city": "Sharjah"})
    s = flow.status(env, firm, eid)
    assert s["status"] == "stale" and s["stale_reasons"] == ["profile_changed"]


def test_approvals_frozen_returns_503(env: Env) -> None:
    from sqlalchemy import text

    firm = env.firm()
    eid = flow.ready_entity(env, firm)
    with env.admin.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO system_flags (key, value, reason, set_by, set_at) "
                "VALUES ('approvals_frozen', true, 'Incident drill', :v, now())"
            ),
            {"v": env.publisher_id},
        )
    _, res = flow.draft_and_approve(env, firm, eid)
    assert res.status_code == 503 and res.json()["reason"] == "approvals_frozen"


def test_repeat_run_is_identical(env: Env) -> None:
    """UT-12 through the worker: same inputs and versions give the same run and result hash."""
    firm = env.firm()
    eid = flow.ready_entity(env, firm)
    first = flow.status(env, firm, eid)["run_id"]
    again = flow.run(env, firm, eid)
    assert again["id"] == first
