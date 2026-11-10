"""Shared synthetic builders for tests (no real data)."""

from __future__ import annotations

import json
from typing import Any

from pintae_rulepacks import fixture_path, load_data
from pintae_rules.calendar import Calendar, calendar_from_data
from pintae_rules.engine import EngineResult, run
from pintae_rules.fixtures import build_input
from pintae_rules.packs import RulePack, pack_from_data

TRN_OK = "100234567800003"


def rp1() -> RulePack:
    return pack_from_data(load_data("RP-1"))


def cal(code: str = "CAL-2") -> Calendar:
    return calendar_from_data(load_data(code))


def rp1_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = json.loads(fixture_path("RP-1").read_text())
    return cases


GOOD_SELLER: dict[str, str | None] = {
    "vat_registered": "yes",
    "trn": TRN_OK,
    "registration_type": "TL",
    "licence_number": "CN-1234567",
    "licence_authority": "Dubai DET",
    "address_line": "Office 1, Synthetic Tower",
    "city": "Dubai",
    "country_code": "AE",
    "emirate": "DXB",
}


def customer(**kw: Any) -> dict[str, Any]:
    base = {
        "customer_id": "C1",
        "name": "Synthetic Buyer LLC",
        "buyer_class": "uae_business",
        "trn": TRN_OK,
        "address_line": "Unit 2",
        "city": "Dubai",
        "country_code": "AE",
        "emirate": "DXB",
        "legal_reg_type": "TL",
        "legal_reg_id": "CN-7654321",
        "legal_reg_authority": "Dubai DET",
    }
    base.update(kw)
    return base


def item(**kw: Any) -> dict[str, Any]:
    base = {
        "item_id": "I1",
        "name": "Widget",
        "description": "Synthetic widget",
        "unit": "H87",
        "net_price": "5.00",
        "gross_price": "5.00",
        "base_quantity": "1",
        "tax_category": "S",
        "tax_rate": "5",
    }
    base.update(kw)
    return base


def invoice_line(**kw: Any) -> dict[str, Any]:
    base = {
        "invoice_number": "INV-1",
        "issue_date": "2027-02-01",
        "due_date": "2027-03-01",
        "document_type": "380",
        "customer_id": "C1",
        "currency": "AED",
        "exchange_rate": None,
        "payment_means": "30",
        "quantity": "2000",
        "unit": "H87",
        "unit_price": "5.00",
        "line_net": "10000.00",
        "tax_category": "S",
        "tax_rate": "5",
        "invoice_net_total": "10000.00",
        "invoice_tax_total": "500.00",
        "invoice_total": "10500.00",
        "transaction_flags": "00000000",
    }
    base.update(kw)
    return base


def clean_case(**overrides: Any) -> dict[str, Any]:
    case: dict[str, Any] = {
        "seller": dict(GOOD_SELLER),
        "datasets": {
            "customers": {"rows": [customer()]},
            "items": {"rows": [item()]},
            "invoices": {"rows": [invoice_line()]},
        },
        "value_maps": [],
        "segment": "SEG-S",
    }
    case.update(overrides)
    return case


def run_case(case: dict[str, Any], calendar_code: str = "CAL-2") -> EngineResult:
    return run(rp1(), build_input(case, cal(calendar_code).provisions))
