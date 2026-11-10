"""API-level flow helpers for integration tests (synthetic data only)."""

from __future__ import annotations

import secrets
from collections.abc import Sequence
from typing import Any

from tests.fixtures import synthetic as fx
from tests.integration.conftest import Env, Firm, upload

__all__ = ["Any", "Env", "Firm", "upload"]

CLEAN_PROFILE = {
    "vat_registered": "yes",
    "trn": "100234567800003",
    "registration_type": "TL",
    "licence_number": "CN-1234567",
    "licence_authority": "Dubai DET",
    "address_line": "Office 1, Synthetic Tower",
    "city": "Dubai",
    "country_code": "AE",
    "emirate_code": "DXB",
}


def clean_files() -> dict[str, tuple[str, bytes]]:
    customers: list[Sequence[object]] = [
        fx.CUSTOMER_HEADERS,
        *[
            [
                f"C{i:03d}",
                f"Synthetic Customer {i:03d} LLC",
                "uae_business",
                fx.synthetic_trn(i),
                None,
                f"Unit {i}",
                "Dubai",
                "AE",
                "DXB",
                "TL",
                f"CN-{i:07d}",
                "Dubai DET",
                None,
                None,
            ]
            for i in range(1, 4)
        ],
    ]
    items: list[list[object]] = [
        fx.ITEM_HEADERS,
        ["I001", "Widget", "Synthetic widget", "H87", "5.00", "5.00", "1", "S", "5"],
    ]
    invoices: list[Sequence[object]] = [
        fx.INVOICE_HEADERS,
        *[
            [
                f"INV-{i}",
                "2026-10-01",
                "2026-10-31",
                "380",
                f"C{i:03d}",
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
            for i in range(1, 4)
        ],
    ]
    return {
        "customers": ("customers.csv", fx.csv_bytes(customers)),
        "items": ("items.csv", fx.csv_bytes(items)),
        "invoices": ("invoices.csv", fx.csv_bytes(invoices)),
    }


def new_entity(
    env: Env,
    firm: Firm,
    name: str = "Synthetic Client LLC",
    profile: dict[str, Any] | None = None,
    revenue_band: str = "lt_50m",
    approve_segment: bool = True,
) -> str:
    c = env.client
    r = c.post("/api/v1/entities", headers=firm.h("preparer"), json={"legal_name": name})
    assert r.status_code == 201, r.text
    eid: str = r.json()["id"]
    r = c.patch(
        f"/api/v1/entities/{eid}", headers=firm.h("preparer"), json=profile or CLEAN_PROFILE
    )
    assert r.status_code == 200, r.text
    r = c.post(
        f"/api/v1/entities/{eid}/segment-assessments",
        headers=firm.h("preparer"),
        json={"entity_type": "person", "revenue_band": revenue_band},
    )
    assert r.status_code == 201, r.text
    if approve_segment:
        r = c.post(
            f"/api/v1/segment-assessments/{r.json()['id']}/decision",
            headers=firm.h("reviewer"),
            json={"decision": "approve"},
        )
        assert r.status_code == 200, r.text
    return eid


def upload_all(
    env: Env, firm: Firm, eid: str, files: dict[str, tuple[str, bytes]]
) -> dict[str, str]:
    ids = {}
    for ds, (name, data) in files.items():
        r = upload(env, firm, eid, ds, name, data)
        assert r.status_code in (200, 202), r.text
        ids[ds] = r.json()["id"]
    env.drain()
    return ids


def confirm_mappings(
    env: Env,
    firm: Firm,
    upload_ids: dict[str, str],
    *,
    absent: dict[str, list[str]] | None = None,
    approve: bool = True,
) -> dict[str, str]:
    c = env.client
    mapping_ids = {}
    for ds, uid in upload_ids.items():
        m = c.get(f"/api/v1/uploads/{uid}/mapping", headers=firm.h("preparer")).json()
        fields = {f: (v if v is not None else "absent") for f, v in m["mapping"]["fields"].items()}
        for f in (absent or {}).get(ds, []):
            fields[f] = "absent"
        r = c.put(
            f"/api/v1/uploads/{uid}/mapping",
            headers=firm.h("preparer"),
            json={
                "sheet": m["mapping"]["sheet"],
                "header_row": m["mapping"]["header_row"],
                "fields": fields,
            },
        )
        assert r.status_code == 200, r.text
        r = c.post(f"/api/v1/uploads/{uid}/mapping/confirm", headers=firm.h("preparer"))
        assert r.status_code == 200, r.text
        mapping_ids[ds] = r.json()["id"]
        if approve:
            r = c.post(
                f"/api/v1/mappings/{mapping_ids[ds]}/decision",
                headers=firm.h("reviewer"),
                json={"decision": "approve"},
            )
            assert r.status_code == 200, r.text
    return mapping_ids


def run(env: Env, firm: Firm, eid: str) -> dict[str, Any]:
    r = env.client.post(
        f"/api/v1/entities/{eid}/runs",
        headers=firm.h("preparer", **{"Idempotency-Key": secrets.token_hex(8)}),
    )
    assert r.status_code == 202, r.text
    env.drain()
    got: dict[str, Any] = env.client.get(f"/api/v1/runs/{r.json()['id']}", headers=firm.h()).json()
    assert got["state"] == "succeeded", got
    return got


def status(env: Env, firm: Firm, eid: str) -> dict[str, Any]:
    r = env.client.get(f"/api/v1/entities/{eid}", headers=firm.h())
    assert r.status_code == 200, r.text
    body: dict[str, Any] = r.json()
    return body


def ready_entity(env: Env, firm: Firm, name: str = "Synthetic Client LLC") -> str:
    eid = new_entity(env, firm, name)
    ids = upload_all(env, firm, eid, clean_files())
    confirm_mappings(env, firm, ids)
    run(env, firm, eid)
    return eid


def draft_and_approve(env: Env, firm: Firm, eid: str) -> tuple[dict[str, Any], Any]:
    rep = env.client.post(f"/api/v1/entities/{eid}/reports", headers=firm.h("preparer"))
    assert rep.status_code == 201, rep.text
    body = rep.json()
    res = env.client.post(
        f"/api/v1/reports/{body['id']}/approve",
        headers=firm.h("reviewer"),
        json={"pins": body["pins"]},
    )
    return body, res
