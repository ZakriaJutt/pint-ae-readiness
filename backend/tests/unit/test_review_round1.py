"""Regression tests for review round 1 (B1-001 to B1-010), engine and status level."""

from __future__ import annotations

from datetime import date

from pintae_rules.calendar import deadline_view
from pintae_rules.segment import BOUNDARY_FLAG, SegmentFacts, classify
from pintae_rules.status import (
    Counts,
    EntityState,
    Status,
    Versions,
    base_status,
    can_be_data_ready,
    effective_status,
    summarise,
)
from tests.helpers import GOOD_SELLER, cal, clean_case, customer, invoice_line, run_case

TODAY = date(2026, 11, 11)


def blockers(res, dataset: str | None = None) -> list[tuple[str, str, str]]:  # type: ignore[no-untyped-def]
    return [
        (f.rule_code, f.record_key, f.outcome)
        for f in res.findings
        if f.severity == "blocker"
        and f.outcome in ("fail", "not_checked", "manual_review")
        and (dataset is None or f.dataset == dataset)
    ]


# B1-003 ---------------------------------------------------------------------------------


def test_a1_buyer_country_uae_spelling_requires_emirate() -> None:
    c = clean_case()
    for spelling in ("UAE", "United Arab Emirates", "u.a.e.", "ARE", "ae"):
        c["datasets"]["customers"]["rows"] = [customer(country_code=spelling, emirate=None)]
        r = run_case(c)
        assert r.outcome("RC-06", "C1") == "fail", spelling
        assert any(f.field == "emirate" for f in r.findings if f.rule_code == "RC-06")


def test_a2_seller_country_free_text_with_unknown_emirate_blocks() -> None:
    r = run_case({"seller": dict(GOOD_SELLER, country_code="United Arab Emirates", emirate=None)})
    assert r.outcome("RC-04", "seller") == "not_checked"


def test_country_code_validated_and_normalised() -> None:
    c = clean_case()
    c["datasets"]["customers"]["rows"] = [
        customer(buyer_class="foreign", country_code="XX", emirate=None)
    ]
    assert run_case(c).outcome("RC-06", "C1") == "fail"
    c["datasets"]["customers"]["rows"] = [
        customer(buyer_class="foreign", country_code="gb", emirate=None)
    ]
    assert run_case(c).outcome("RC-06", "C1") == "pass"
    c["datasets"]["customers"]["rows"] = [
        customer(buyer_class="foreign", country_code="Albion", emirate=None)
    ]
    assert run_case(c).outcome("RC-06", "C1") == "not_checked"
    c["value_maps"] = [["country", "Albion", "GB"]]
    assert run_case(c).outcome("RC-06", "C1") == "pass"
    c["datasets"]["customers"]["rows"] = [customer(country_code="UAE", emirate="DXB")]
    c["value_maps"] = []
    assert run_case(c).outcome("RC-06", "C1") == "pass"


# B1-004 ---------------------------------------------------------------------------------


def test_a5_conflicting_customer_rows_keep_invoice_in_scope() -> None:
    c = clean_case()
    c["datasets"]["customers"]["rows"] = [customer(buyer_class="consumer"), customer()]
    c["datasets"]["invoices"]["rows"] = [invoice_line(invoice_total="99999.00")]
    r = run_case(c)
    assert [s.scope for s in r.records if s.dataset == "invoices"] == ["in_scope"]
    b = blockers(r)
    assert ("RC-21", "C1", "fail") in b and ("RC-21", "INV-1", "not_checked") in b
    assert ("RC-17", "INV-1", "fail") in b


def test_identical_duplicate_customer_rows_are_not_a_conflict() -> None:
    c = clean_case()
    c["datasets"]["customers"]["rows"] = [customer(), customer()]
    r = run_case(c)
    assert not [b for b in blockers(r) if b[0] == "RC-21"]


def test_invoice_customer_not_in_customers_file_fails() -> None:
    c = clean_case()
    c["datasets"]["invoices"]["rows"] = [invoice_line(customer_id="C9")]
    assert run_case(c).outcome("RC-21", "INV-1") == "fail"


# B1-006 ---------------------------------------------------------------------------------


def test_transaction_type_code_is_blocking() -> None:
    c = clean_case()
    c["datasets"]["invoices"]["fields"] = {"transaction_flags": "absent"}
    r = run_case(c)
    f = next(x for x in r.findings if x.rule_code == "RC-19")
    assert (f.severity, f.outcome) == ("blocker", "not_checked")
    c["datasets"]["invoices"]["fields"] = {}
    c["datasets"]["invoices"]["rows"] = [invoice_line(transaction_flags="0000")]
    assert ("RC-19", "INV-1", "fail") in blockers(run_case(c))


# B1-007 ---------------------------------------------------------------------------------


def _commercial(**kw: str | None) -> dict[str, str | None]:
    return invoice_line(
        document_type="480",
        tax_category="O",
        tax_rate=None,
        invoice_tax_total="0.00",
        invoice_total="10000.00",
        **kw,
    )


def test_a4_commercial_invoice_without_customer_link_is_not_checked() -> None:
    c = clean_case()
    c["datasets"]["customers"]["rows"] = [customer(legal_reg_type=None, legal_reg_id=None)]
    c["datasets"]["invoices"]["rows"] = [_commercial()]
    c["datasets"]["invoices"]["fields"] = {"customer_id": "absent"}
    r = run_case(c)
    assert r.outcome("RC-08", "INV-1", "invoices") == "not_checked"
    c["datasets"]["invoices"]["fields"] = {}
    c["datasets"]["invoices"]["rows"] = [_commercial(customer_id=None)]
    assert run_case(c).outcome("RC-08", "INV-1", "invoices") == "not_checked"
    # With a readable link the customer-level rule decides.
    c["datasets"]["invoices"]["rows"] = [_commercial()]
    r = run_case(c)
    assert r.outcome("RC-08", "INV-1", "invoices") == "pass"
    assert r.outcome("RC-08", "C1", "customers") == "fail"


def test_tax_invoice_does_not_need_buyer_legal_registration() -> None:
    c = clean_case()
    c["datasets"]["invoices"]["fields"] = {"customer_id": "absent"}
    assert run_case(c).outcome("RC-08", "INV-1", "invoices") is None


# MF 24 ----------------------------------------------------------------------------------


def test_tin_only_buyer_is_accepted_with_a_warning_finding() -> None:
    c = clean_case()
    c["datasets"]["customers"]["rows"] = [customer(trn=None, tin="1002345678")]
    r = run_case(c)
    assert r.outcome("RC-07", "C1") == "pass"
    f = next(x for x in r.findings if x.rule_code == "RC-22")
    assert (f.severity, f.outcome) == ("warning", "fail")


# B1-008 ---------------------------------------------------------------------------------


def test_a6_not_checked_line_kept_beside_failed_line() -> None:
    c = clean_case()
    c["datasets"]["invoices"]["rows"] = [
        invoice_line(unit="ZZZ", quantity="1000", line_net="5000.00"),
        invoice_line(unit="pieces", quantity="1000", line_net="5000.00"),
    ]
    r = run_case(c)
    outcomes = sorted(f.outcome for f in r.findings if f.rule_code == "RC-14")
    assert outcomes == ["fail", "not_checked"]
    fail = next(f for f in r.findings if f.rule_code == "RC-14" and f.outcome == "fail")
    assert fail.fingerprint == "RC-14|invoices|INV-1|unit"  # exception key unchanged


# B1-010 and the AED 50M boundary --------------------------------------------------------


def test_seg_n_unknown_first_invoice_needs_a_date() -> None:
    for state in ("unknown", None):
        v = deadline_view(cal(), "SEG-N", TODAY, first_invoice_state=state)
        assert v.display == "First invoice date needed" and v.appoint_by_passed
        assert v.flags == ("first_invoice_date_needed",)
    v = deadline_view(cal(), "SEG-N", TODAY, first_invoice_state="not_yet")
    assert v.display == "Before first invoice" and not v.appoint_by_passed


def test_revenue_exactly_50m_is_segment_ambiguous_with_earlier_deadline() -> None:
    seg = classify(SegmentFacts("person", "eq_50m"))
    assert seg == "SEG-U"
    v = deadline_view(cal(), seg, TODAY, revenue_band="eq_50m")
    assert v.governing_appoint_by == date(2026, 10, 30) and not v.segment_confirmed
    assert v.flags == (BOUNDARY_FLAG,) and any("exceed AED 50 million" in n for n in v.notes)
    assert {o.segment for o in v.outcomes} == {"SEG-L", "SEG-S"}


# B1-002, B1-001, B1-005 at status level -------------------------------------------------


def test_empty_required_dataset_is_checks_incomplete_never_ready() -> None:
    counts = summarise(
        [], [], {"customers": 1, "items": 1}, {"customers": 1, "items": 1, "invoices": 0}
    )
    assert counts.empty_datasets == ("invoices",)
    e = EntityState(True, "SEG-S", frozenset({"customers", "items", "invoices"}), True)
    assert (
        base_status(e, counts, mappings_approved=True, reviewer_approved=True)
        is Status.CHECKS_INCOMPLETE
    )
    assert not can_be_data_ready(counts, True)
    clean = Counts(0, 0, 0, 0, 0)
    assert can_be_data_ready(clean, True)


def test_calendar_and_upload_changes_are_stale_reasons() -> None:
    v1 = Versions("RP-1", 1, {}, 1, "CAL-2", {"invoices": "u1"})
    assert effective_status(
        Status.DATA_READY, v1, Versions("RP-1", 1, {}, 1, "CAL-3", {"invoices": "u1"}), TODAY, TODAY
    ) == (Status.STALE, ["calendar_changed"])
    assert effective_status(
        Status.DATA_READY, v1, Versions("RP-1", 1, {}, 1, "CAL-2", {"invoices": "u2"}), TODAY, TODAY
    ) == (Status.STALE, ["upload_changed"])


# Round 2 ---------------------------------------------------------------------------------


def _gov(**kw: str | None) -> dict[str, str | None]:
    return customer(
        buyer_class="government",
        trn=None,
        tin=None,
        legal_reg_type=None,
        legal_reg_id=None,
        legal_reg_authority=None,
        **kw,
    )


def test_b1_013_government_buyer_without_tin_is_checked_with_endpoint_absent_or_empty() -> None:
    c = clean_case()
    c["datasets"]["customers"]["rows"] = [_gov()]
    c["datasets"]["customers"]["fields"] = {"endpoint_id": "absent"}
    assert run_case(c).outcome("RC-08", "C1", "customers") == "fail"
    c["datasets"]["customers"]["fields"] = {}
    c["datasets"]["customers"]["rows"] = [_gov(endpoint_id=None)]
    assert run_case(c).outcome("RC-08", "C1", "customers") == "fail"
    c["datasets"]["customers"]["rows"] = [_gov(endpoint_id="0235:GOV-ADDRESS")]
    assert run_case(c).outcome("RC-08", "C1", "customers") == "fail"
    # A TIN-based endpoint does not need IBT-047 (IBR-149-AE).
    c["datasets"]["customers"]["rows"] = [_gov(endpoint_id="1002345678")]
    assert run_case(c).outcome("RC-08", "C1", "customers") is None
    # With the registration given, the check passes.
    c["datasets"]["customers"]["rows"] = [
        customer(buyer_class="government", trn=None, tin=None, endpoint_id=None)
    ]
    assert run_case(c).outcome("RC-08", "C1", "customers") == "pass"


def test_seg_n_invoices_already_dated_is_flagged_passed() -> None:
    v = deadline_view(
        cal(), "SEG-N", TODAY, first_invoice_state="not_yet", earliest_invoice_on=date(2026, 10, 1)
    )
    assert v.appoint_by_passed and v.flags == ("invoices_dated_before_today",)
    v = deadline_view(
        cal(), "SEG-N", TODAY, first_invoice_state="not_yet", earliest_invoice_on=date(2026, 12, 1)
    )
    assert not v.appoint_by_passed and v.display == "Before first invoice"
