"""Parsers and dictionary mapper (IT-08 file checks at parser level; T-3.1.2 accuracy)."""

from __future__ import annotations

import pytest

from pintae_ingest.mapper import (
    ABSENT,
    TARGET_FIELDS,
    MappingError,
    apply_mapping,
    header_fingerprint,
    suggest,
    validate_for_confirm,
)
from pintae_ingest.parsers import RejectFile, cell_text, parse
from tests.fixtures import synthetic as fx


@pytest.mark.parametrize(
    ("name", "data", "reason"),
    [
        ("big.csv", fx.oversized_csv(), "too_large"),
        ("bomb.xlsx", fx.expanding_xlsx(), "expands_too_large"),
        ("entity.xlsx", fx.external_entity_xlsx(), "external_entity"),
        ("macro.xlsx", fx.macro_renamed_xlsx(), "macro_content"),
        ("corrupt.xlsx", fx.fx_e_corrupt(), "parse_failed"),
        ("notes.txt", b"hello", "unsupported_type"),
    ],
)
def test_it08_rejections_have_specific_reasons(name: str, data: bytes, reason: str) -> None:
    with pytest.raises(RejectFile) as exc:
        parse(data, name)
    assert exc.value.reason_code == reason


def test_cells_kept_as_exact_text() -> None:
    assert cell_text(10500.01) == "10500.01"
    assert cell_text(5.0) == "5"
    assert cell_text(3.6725001) == "3.6725001"


def test_fx_a_maps_fully_with_dictionary() -> None:
    files = fx.fx_a_files()
    for ds, (name, data) in files.items():
        s = suggest(ds, parse(data, name))
        unmapped = [f for f, v in s.mapping.items() if v is None]
        assert unmapped == [], (ds, unmapped)


def test_fx_c_quickbooks_headers() -> None:
    s = suggest("invoices", parse(fx.fx_c_invoices_qbo(), "qbo.csv"))
    assert s.mapping["invoice_number"] == "Invoice No"
    assert s.mapping["quantity"] == "Qty"
    assert s.mapping["unit_price"] == "Rate"
    assert s.mapping["line_net"] == "Amount"
    assert s.mapping["exchange_rate"] == "Exchange Rate"


def test_fx_d_second_header_row_is_chosen() -> None:
    parsed = parse(fx.fx_d_invoices_odoo(), "odoo.xlsx")
    s = suggest("invoices", parsed)
    assert s.header_row == 2
    assert s.mapping["invoice_number"] == "Number"
    assert s.mapping["invoice_net_total"] == "Untaxed Amount"
    rows = apply_mapping(
        "u1",
        s.sheet,
        s.header_row,
        s.headers,
        parsed.sheets[0].rows,
        {k: v for k, v in s.mapping.items() if v},
    )
    assert [r.row_number for r in rows.rows] == [3]


def test_confirm_requires_every_field_mapped_or_absent() -> None:
    parsed = parse(fx.fx_d_invoices_odoo(), "odoo.xlsx")
    s = suggest("invoices", parsed)
    with pytest.raises(MappingError, match="neither mapped"):
        validate_for_confirm("invoices", s.mapping, s.headers)
    full = {f: (v if v is not None else ABSENT) for f, v in s.mapping.items()}
    validate_for_confirm("invoices", full, s.headers)
    full["invoice_number"] = "No such column"
    with pytest.raises(MappingError, match="not in the header row"):
        validate_for_confirm("invoices", full, s.headers)


def test_fingerprint_ignores_case_and_spacing() -> None:
    assert header_fingerprint(["Invoice No", "Qty"]) == header_fingerprint(["invoice no", "QTY "])
    assert header_fingerprint(["Invoice No"]) != header_fingerprint(["Invoice"])


def test_first_suggestion_accuracy_fx_a_to_d() -> None:
    """Measured, not asserted against the 85% [P] threshold (TRD 8.9): recorded in the report."""
    expected = {
        "qbo": {
            "invoice_number": "Invoice No",
            "issue_date": "Invoice Date",
            "due_date": "Due Date",
            "customer_id": "Customer",
            "currency": "Currency",
            "exchange_rate": "Exchange Rate",
            "item_id": "Product/Service",
            "quantity": "Qty",
            "unit_price": "Rate",
            "line_net": "Amount",
            "tax_category": "Tax Code",
            "tax_rate": "Tax Rate",
            "invoice_total": "Total",
        },
        "odoo": {
            "invoice_number": "Number",
            "issue_date": "Invoice/Bill Date",
            "customer_id": "Partner",
            "invoice_net_total": "Untaxed Amount",
            "tax_category": "Taxes",
            "invoice_total": "Total",
        },
    }
    got = {
        "qbo": suggest("invoices", parse(fx.fx_c_invoices_qbo(), "q.csv")).mapping,
        "odoo": suggest("invoices", parse(fx.fx_d_invoices_odoo(), "o.xlsx")).mapping,
    }
    right = sum(got[k][f] == v for k, exp in expected.items() for f, v in exp.items())
    total = sum(len(e) for e in expected.values())
    assert right / total >= 0.85
    assert len(TARGET_FIELDS["invoices"]) == 21
