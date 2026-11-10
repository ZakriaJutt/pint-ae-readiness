"""IT-03, IT-06 (upload part), IT-08 (API and worker), IT-15, IT-04, IT-05, IT-10, FX-A run."""

from __future__ import annotations

import io
import json
import logging
import uuid

from sqlalchemy import func, select, text

from pintae_core import jobs, tenancy
from pintae_core.logging import JsonFormatter
from pintae_core.models import Job, Upload
from pintae_worker.main import process
from tests.fixtures import synthetic as fx
from tests.integration import flow
from tests.integration.conftest import Env, upload


def test_it03_same_bytes_once_per_entity_and_dataset(env: Env) -> None:
    firm = env.firm()
    e1 = flow.new_entity(env, firm, "One LLC")
    e2 = flow.new_entity(env, firm, "Two LLC", {**flow.CLEAN_PROFILE, "trn": "100000000000203"})
    name, data = flow.clean_files()["customers"]
    r1 = upload(env, firm, e1, "customers", name, data)
    r2 = upload(env, firm, e1, "customers", name, data)
    r3 = upload(env, firm, e2, "customers", name, data)
    assert r1.status_code == 202 and r2.status_code == 200 and r2.json()["duplicate"] is True
    assert r2.json()["id"] == r1.json()["id"] and r3.json()["id"] != r1.json()["id"]
    with tenancy.session(firm.id, env.app) as s:
        assert s.execute(select(func.count()).select_from(Upload)).scalar_one() == 2


def test_idempotency_key_replays_and_rejects_reuse(env: Env) -> None:
    firm = env.firm()
    eid = flow.new_entity(env, firm)
    name, data = flow.clean_files()["customers"]
    h = firm.h("preparer", **{"Idempotency-Key": "same-key"})
    a = env.client.post(
        f"/api/v1/entities/{eid}/uploads",
        headers=h,
        data={"dataset": "customers"},
        files={"file": (name, data)},
    )
    b = env.client.post(
        f"/api/v1/entities/{eid}/uploads",
        headers=h,
        data={"dataset": "customers"},
        files={"file": (name, data)},
    )
    assert a.json() == b.json()
    c = env.client.post(
        f"/api/v1/entities/{eid}/uploads",
        headers=h,
        data={"dataset": "items"},
        files={"file": (name, data)},
    )
    assert c.status_code == 422
    assert (
        env.client.post(
            f"/api/v1/entities/{eid}/uploads",
            headers=firm.h(),
            data={"dataset": "items"},
            files={"file": (name, data)},
        ).status_code
        == 422
    )  # key required


def test_it06_it08_fx_a_parsed_and_bad_files_rejected_with_reasons(env: Env) -> None:
    firm = env.firm()
    eid = flow.new_entity(env, firm)
    ids = flow.upload_all(env, firm, eid, fx.fx_a_files())
    big = upload(env, firm, eid, "customers", "big.csv", fx.oversized_csv())
    assert big.status_code == 422 and big.json()["reason"] == "too_large"
    txt = upload(env, firm, eid, "customers", "notes.txt", b"x")
    assert txt.json()["reason"] == "unsupported_type"
    bad = {
        "corrupt.xlsx": fx.fx_e_corrupt(),
        "bomb.xlsx": fx.expanding_xlsx(),
        "entity.xlsx": fx.external_entity_xlsx(),
        "macro.xlsx": fx.macro_renamed_xlsx(),
    }
    bad_ids = {n: upload(env, firm, eid, "items", n, d).json()["id"] for n, d in bad.items()}
    results = env.drain()
    assert results == ["succeeded"] * 4  # rejection is a terminal outcome, not a crash
    got = {
        u: env.client.get(f"/api/v1/uploads/{u}", headers=firm.h()).json()
        for u in list(ids.values())
    }
    assert [g["state"] for g in got.values()] == ["parsed"] * 3
    reasons = {
        n: env.client.get(f"/api/v1/uploads/{u}", headers=firm.h()).json()
        for n, u in bad_ids.items()
    }
    assert {n: (r["state"], r["reject_reason"]) for n, r in reasons.items()} == {
        "corrupt.xlsx": ("rejected", "parse_failed"),
        "bomb.xlsx": ("rejected", "expands_too_large"),
        "entity.xlsx": ("rejected", "external_entity"),
        "macro.xlsx": ("rejected", "macro_content"),
    }
    assert env.client.get("/readyz").status_code in (200, 503)  # worker path stayed healthy


def test_fx_a_seeded_defects_are_found(env: Env) -> None:
    firm = env.firm()
    eid = flow.new_entity(env, firm, "Al Noor Trading LLC")
    ids = flow.upload_all(env, firm, eid, fx.fx_a_files())
    flow.confirm_mappings(env, firm, ids)
    flow.run(env, firm, eid)
    items = env.client.get(f"/api/v1/entities/{eid}/findings", headers=firm.h()).json()["items"]

    def keys(rule: str, outcome: str) -> set[str]:
        return {f["record_key"] for f in items if f["rule"] == rule and f["outcome"] == outcome}

    assert keys("RC-07", "fail") == {f"C{i:03d}" for i in range(1, 7)}
    assert keys("RC-06", "not_checked") == {
        "C007",
        "C008",
        "C009",
    }  # "Dubayy" needs a value mapping
    assert keys("RC-14", "not_checked") == {"I001", "I002", "I003", "I004"}  # "pcs" unmapped
    # The duplicate number merges two invoices, so its totals cannot agree either.
    assert keys("RC-17", "fail") == {"INV-0010", "INV-0020", "INV-0299"}
    assert keys("RC-09", "fail") == {"INV-0299"}
    assert keys("RC-05", "out_of_scope") == {f"C{i:03d}" for i in range(36, 41)}
    f = next(x for x in items if x["rule"] == "RC-17")
    assert f["sheet"] == "Invoices" and f["column"] and f["row"] > 1  # source evidence
    s = flow.status(env, firm, eid)
    assert s["status"] == "gaps_open"
    assert s["counts"]["score_by_dataset"]["customers"]["in_scope"] == 35


def test_it15_two_firms_same_file_name_distinct_keys(env: Env) -> None:
    a, b = env.firm("A"), env.firm("B")
    ea = flow.new_entity(env, a, "A LLC")
    eb = flow.new_entity(env, b, "B LLC")
    name, data = flow.clean_files()["customers"]
    upload(env, a, ea, "customers", "customers.xlsx" if False else name, data)
    upload(env, b, eb, "customers", name, data)
    with env.admin.connect() as conn:
        rows = conn.execute(text("SELECT firm_id, storage_key FROM uploads")).all()
    assert len({k for _, k in rows}) == 2
    for fid, key in rows:
        assert key.startswith(f"firms/{fid}/entities/") and "/source-customers/" in key
        assert name not in key


def _queued_parse_job(env: Env) -> tuple[flow.Any, uuid.UUID]:
    firm = env.firm()
    eid = flow.new_entity(env, firm)
    name, data = flow.clean_files()["customers"]
    r = upload(env, firm, eid, "customers", name, data)
    return firm, uuid.UUID(r.json()["job_id"])


def test_it04_superseded_attempt_is_discarded_and_state_never_regresses(env: Env) -> None:
    firm, job_id = _queued_parse_job(env)
    first = jobs.claim(env.app, 300)
    assert first is not None and first.job_id == job_id
    with env.admin.begin() as conn:  # lease expires while attempt 1 is still "working"
        conn.execute(
            text("UPDATE jobs SET lease_expires_at = now() - interval '1 second' WHERE id = :j"),
            {"j": job_id},
        )
    assert jobs.requeue_expired(env.app) == 1
    second = jobs.claim(env.app, 300)
    assert second is not None and second.attempt_id != first.attempt_id
    assert process(env.app, env.store, first) == "discarded"
    assert process(env.app, env.store, second) == "succeeded"
    assert process(env.app, env.store, second) == "discarded"  # duplicate delivery
    with tenancy.session(firm.id, env.app) as s:
        job = s.get(Job, job_id)
        assert job is not None and job.state == "succeeded"
        with tenancy.session(firm.id, env.app) as s2:
            assert jobs.mark_failed_or_retry(s2, first, "late") == "discarded"
    with tenancy.session(firm.id, env.app) as s:
        assert s.get(Job, job_id).state == "succeeded"  # type: ignore[union-attr]


def test_it05_result_visible_after_client_stopped_polling(env: Env) -> None:
    firm, job_id = _queued_parse_job(env)
    env.drain()  # nobody is polling; the job completes anyway
    with tenancy.session(firm.id, env.app) as s:
        up = s.execute(select(Upload)).scalar_one()
    assert env.client.get(f"/api/v1/uploads/{up.id}", headers=firm.h()).json()["state"] == "parsed"
    assert env.client.get(f"/api/v1/jobs/{job_id}", headers=firm.h()).json()["state"] == "succeeded"


def test_failed_attempt_retries_then_fails_by_budget(env: Env) -> None:
    _firm, job_id = _queued_parse_job(env)
    with env.admin.begin() as conn:
        key = conn.execute(text("SELECT storage_key FROM uploads")).scalar_one()
    env.store.delete(key)  # storage read fails
    assert env.drain() == ["queued"]
    with env.admin.begin() as conn:
        row = conn.execute(
            text("SELECT state, attempts, last_error_code FROM jobs WHERE id = :j"), {"j": job_id}
        ).one()
    assert (
        row.state == "queued" and row.attempts == 1 and row.last_error_code == "FileNotFoundError"
    )


def test_it10_no_cell_values_in_logs_and_one_correlation_id(env: Env) -> None:
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.addHandler(handler)
    try:
        firm = env.firm()
        eid = flow.new_entity(env, firm, "Al Noor Trading LLC")
        name, data = fx.fx_a_files()["customers"]
        r = upload(env, firm, eid, "customers", name, data)
        cid = r.headers["X-Correlation-ID"]
        env.drain()
        ids = {"customers": r.json()["id"]}
        flow.confirm_mappings(env, firm, ids)
        flow.run(env, firm, eid)
    finally:
        root.removeHandler(handler)
    out = buf.getvalue()
    assert out
    for needle in (
        fx.synthetic_trn(10),
        "100234567800003",
        "Synthetic Customer 010 LLC",
        "Al Noor",
        "Dubayy",
    ):
        assert needle not in out, needle
    lines = [json.loads(x) for x in out.splitlines() if x.startswith("{")]
    job_lines = [
        x
        for x in lines
        if x.get("event") == "job.succeeded" and x.get("job_kind") == "parse_upload"
    ]
    assert job_lines and all(x["correlation_id"] == cid for x in job_lines)
    with env.admin.connect() as conn:
        assert (
            str(
                conn.execute(
                    text("SELECT correlation_id FROM jobs WHERE kind = 'parse_upload'")
                ).scalar_one()
            )
            == cid
        )
