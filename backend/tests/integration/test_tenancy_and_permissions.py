"""IT-01 (API, worker context, no-context reads), IT-02 (Preparer refused), dashboard
isolation, and database guards (RLS WITH CHECK, snapshot CHECK, decider trigger)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError

from pintae_core import tenancy
from pintae_core.models import TENANT_TABLES, AuditEvent, FindingRow
from tests.integration import flow
from tests.integration.conftest import Env


def _firm_a_objects(env: Env) -> tuple[flow.Any, dict[str, str]]:
    a = env.firm("Firm A")
    eid = flow.new_entity(env, a, "A Client LLC")
    files = flow.clean_files()
    from tests.fixtures import synthetic as fx

    files["customers"] = (
        "customers.csv",
        fx.csv_bytes(
            [
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
                    "DXB",
                    "TL",
                    "CN-1",
                    "Dubai DET",
                    None,
                    None,
                ],
            ]
        ),
    )
    ids = flow.upload_all(env, a, eid, files)
    maps = flow.confirm_mappings(env, a, ids)
    run = flow.run(env, a, eid)
    finding = env.client.get(f"/api/v1/entities/{eid}/findings", headers=a.h()).json()["items"][0]
    rep = env.client.post(f"/api/v1/entities/{eid}/reports", headers=a.h()).json()
    return a, {
        "entity": eid,
        "upload": ids["customers"],
        "mapping": maps["customers"],
        "run": run["id"],
        "finding": finding["id"],
        "report": rep["id"],
        "code": rep["reference_code"],
    }


def test_it01_cross_firm_requests_return_404_with_audit(env: Env) -> None:
    a, o = _firm_a_objects(env)
    b = env.firm("Firm B")
    c = env.client
    calls = [
        c.get(f"/api/v1/entities/{o['entity']}", headers=b.h()),
        c.patch(f"/api/v1/entities/{o['entity']}", headers=b.h(), json={"city": "X"}),
        c.get(f"/api/v1/entities/{o['entity']}/findings", headers=b.h()),
        c.get(f"/api/v1/entities/{o['entity']}/uploads", headers=b.h()),
        c.get(f"/api/v1/uploads/{o['upload']}", headers=b.h()),
        c.get(f"/api/v1/uploads/{o['upload']}/mapping", headers=b.h()),
        c.post(
            f"/api/v1/mappings/{o['mapping']}/decision", headers=b.h(), json={"decision": "approve"}
        ),
        c.get(f"/api/v1/runs/{o['run']}", headers=b.h()),
        c.post(
            f"/api/v1/findings/{o['finding']}/exceptions",
            headers=b.h(),
            json={"reason": "cross firm"},
        ),
        c.get(f"/api/v1/reports/{o['report']}", headers=b.h()),
        c.get(f"/api/v1/reports/lookup?code={o['code']}", headers=b.h()),
        c.post(f"/api/v1/reports/{o['report']}/approve", headers=b.h(), json={"pins": {}}),
        c.post(f"/api/v1/entities/{o['entity']}/runs", headers=b.h(**{"Idempotency-Key": "k1"})),
        flow.upload(env, b, o["entity"], "customers", "c.csv", b"a,b\n1,2\n"),
    ]
    assert [r.status_code for r in calls] == [404] * len(calls), [r.text for r in calls]
    assert all(r.json() == {"reason": "not_found"} for r in calls)
    with tenancy.session(b.id, env.app) as s:
        n = s.execute(
            select(func.count())
            .select_from(AuditEvent)
            .where(AuditEvent.action == "access.not_found")
        ).scalar_one()
    assert n >= len(calls) - 1  # lookup by code has no object id but is still audited
    # Firm A still sees its own data.
    assert c.get(f"/api/v1/entities/{o['entity']}", headers=a.h()).status_code == 200


def test_it01_worker_context_and_no_context_read_zero_rows(env: Env) -> None:
    a, _o = _firm_a_objects(env)
    b = env.firm("Firm B")
    with tenancy.session(b.id, env.app) as s:
        assert s.execute(select(func.count()).select_from(FindingRow)).scalar_one() == 0
        assert s.execute(select(FindingRow).where(FindingRow.firm_id == a.id)).first() is None
    with tenancy.session(a.id, env.app) as s:
        assert s.execute(select(func.count()).select_from(FindingRow)).scalar_one() > 0
    # Application role with no firm set: every tenant table reads zero rows.
    with env.app.connect() as conn:
        assert (
            conn.execute(
                text("SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname = current_user")
            ).scalar_one()
            is False
        )
        for t in TENANT_TABLES:
            assert conn.execute(text(f"SELECT count(*) FROM {t}")).scalar_one() == 0, t
    with env.admin.connect() as conn:  # the rows do exist
        assert conn.execute(text("SELECT count(*) FROM findings")).scalar_one() > 0


def test_rls_with_check_refuses_writes_into_another_firm(env: Env) -> None:
    a = env.firm("Firm A")
    b = env.firm("Firm B")
    with pytest.raises(DBAPIError), tenancy.session(b.id, env.app) as s:
        s.execute(
            text(
                "INSERT INTO client_entities (firm_id, legal_name, source_ledger) VALUES (:f, 'x', 'excel')"
            ),
            {"f": a.id},
        )


def test_snapshot_check_constraint_refuses_false_ready(env: Env) -> None:
    a, o = _firm_a_objects(env)
    with (
        pytest.raises(DBAPIError, match="data_ready_requires_clean"),
        tenancy.session(a.id, env.app) as s,
    ):
        s.execute(
            text("UPDATE readiness_snapshots SET base_status = 'data_ready' WHERE run_id = :r"),
            {"r": uuid.UUID(o["run"])},
        )


def test_audit_events_are_insert_only(env: Env) -> None:
    a, _ = _firm_a_objects(env)
    with pytest.raises(DBAPIError), tenancy.session(a.id, env.app) as s:
        s.execute(text("DELETE FROM audit_events"))


def test_it02_preparer_cannot_decide(env: Env) -> None:
    a, o = _firm_a_objects(env)
    c = env.client
    seg = c.post(
        f"/api/v1/entities/{o['entity']}/segment-assessments",
        headers=a.h("preparer"),
        json={"entity_type": "person", "revenue_band": "ge_50m"},
    ).json()
    calls = [
        c.post(
            f"/api/v1/segment-assessments/{seg['id']}/decision",
            headers=a.h("preparer"),
            json={"decision": "approve"},
        ),
        c.post(
            f"/api/v1/mappings/{o['mapping']}/decision",
            headers=a.h("preparer"),
            json={"decision": "approve"},
        ),
        c.post(
            f"/api/v1/entities/{o['entity']}/value-mappings/decision",
            headers=a.h("preparer"),
            json={"items": [{"kind": "unit", "source_value": "pcs"}], "decision": "approve"},
        ),
        c.post(
            f"/api/v1/exceptions/{uuid.uuid4()}/decision",
            headers=a.h("preparer"),
            json={"decision": "accept"},
        ),
        c.post(
            "/api/v1/findings/review-resolutions",
            headers=a.h("preparer"),
            json={"finding_ids": [o["finding"]], "resolution": "confirmed_self_billed"},
        ),
        c.post(
            f"/api/v1/reports/{o['report']}/approve", headers=a.h("preparer"), json={"pins": {}}
        ),
        c.put(
            f"/api/v1/entities/{o['entity']}/asp-status",
            headers=a.h("preparer"),
            json={"status": "appointed"},
        ),
    ]
    assert [r.status_code for r in calls] == [403] * len(calls)


def test_decider_trigger_backs_the_service_check(env: Env) -> None:
    a, o = _firm_a_objects(env)
    with pytest.raises(DBAPIError, match="Reviewer or Owner"), tenancy.session(a.id, env.app) as s:
        s.execute(
            text("UPDATE column_mappings SET approved_by = :u WHERE id = :m"),
            {"u": a.users["preparer"], "m": uuid.UUID(o["mapping"])},
        )


def test_unauthenticated_requests_are_refused(env: Env) -> None:
    assert env.client.get("/api/v1/dashboard").status_code == 401
    assert (
        env.client.get("/api/v1/dashboard", headers={"Authorization": "Bearer nope"}).status_code
        == 401
    )


def test_disabled_user_session_ends(env: Env) -> None:
    a = env.firm()
    with env.admin.begin() as conn:
        conn.execute(
            text("UPDATE users SET disabled_at = now() WHERE id = :u"), {"u": a.users["preparer"]}
        )
    assert env.client.get("/api/v1/dashboard", headers=a.h("preparer")).status_code == 401
    with env.admin.begin() as conn:
        conn.execute(
            text(
                "UPDATE sessions SET last_seen_at = now() - interval '31 minutes' WHERE user_id = :u"
            ),
            {"u": a.users["owner"]},
        )
    assert env.client.get("/api/v1/dashboard", headers=a.h("owner")).status_code == 401


def test_dashboard_is_per_firm_with_risk_order_and_totals(env: Env) -> None:
    a = env.firm("Firm A")
    b = env.firm("Firm B")

    def prof(i: int) -> dict[str, str]:
        return {**flow.CLEAN_PROFILE, "trn": f"1{i:012d}03"}

    s_ent = flow.new_entity(env, a, "Small Co", prof(1), revenue_band="lt_50m")
    l_ent = flow.new_entity(env, a, "Large Co", prof(2), revenue_band="ge_50m")
    u_ent = flow.new_entity(env, a, "Unknown Co", prof(3), revenue_band="unknown")
    dup = env.client.post("/api/v1/entities", headers=a.h(), json={"legal_name": "Dup"}).json()[
        "id"
    ]
    r = env.client.patch(f"/api/v1/entities/{dup}", headers=a.h(), json={"trn": prof(1)["trn"]})
    assert r.status_code == 409 and r.json()["reason"] == "conflict"
    env.client.patch(f"/api/v1/entities/{dup}", headers=a.h(), json={"legal_name": "Dup"})
    flow.new_entity(env, b, "Other Firm Client", revenue_band="ge_50m")
    env.client.put(
        f"/api/v1/entities/{s_ent}/asp-status",
        headers=a.h("reviewer"),
        json={"status": "appointed", "asp_name": "Synthetic ASP"},
    )
    d = env.client.get("/api/v1/dashboard", headers=a.h()).json()
    order = [r["entity_id"] for r in d["rows"]]
    assert order[0] == l_ent and order[-1] == s_ent  # SEG-L overdue first, appointed SEG-S last
    order.remove(dup)
    assert order == [l_ent, u_ent, s_ent]
    assert d["totals"]["entities"] == 4 == sum(d["totals"]["by_status"].values())
    assert d["totals"]["past_appoint_by_without_asp"] == 3  # SEG-L, SEG-U and the unassessed one
    assert all(r["legal_name"] != "Other Firm Client" for r in d["rows"])
    u = next(r for r in d["rows"] if r["entity_id"] == u_ent)
    assert u["deadline"]["segment_confirmed"] is False and len(u["deadline"]["outcomes"]) == 2
