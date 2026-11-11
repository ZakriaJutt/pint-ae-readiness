"""C1 corrections (2026-11-11): UT-20 (Tax Group exclusion re-sourced to MD 197 of 2026 in
CAL-3) and UT-21 (appointment status and data status stay separate)."""

from __future__ import annotations

import dataclasses
from datetime import date

from pintae_rules.calendar import deadline_view
from pintae_rules.dashboard import SortableRow, overdue_without_asp, risk_sort
from pintae_rules.fixtures import run_suite
from tests.helpers import cal, clean_case, customer, invoice_line, rp1, rp1_cases, run_case


def _prv2_finding_message(day: str, calendar_code: str) -> tuple[str | None, str | None]:
    c = clean_case()
    c["datasets"]["customers"]["rows"] = [customer(buyer_class="vat_group_member")]
    c["datasets"]["invoices"]["rows"] = [invoice_line(issue_date=day)]
    r = run_case(c, calendar_code)
    outcome = r.outcome("RC-05", "INV-1", "invoices") or r.outcome("RC-17", "INV-1")
    msgs = [
        f.message for f in r.findings if f.record_key == "INV-1" and f.outcome == "grace_period"
    ]
    return outcome, (msgs[0] if msgs else None)


def test_ut20_cal3_prv2_is_the_md197_tax_group_exclusion() -> None:
    prv2 = next(p for p in cal("CAL-3").provisions if p.code == "PRV-2")
    assert prv2.applies_from == date(2027, 1, 1)
    assert prv2.applies_to == date(2028, 12, 31)  # 24 months from 1 January 2027
    assert prv2.selector == {"buyer_class": "vat_group_member"}
    assert prv2.effect == "exclude_from_denominator"
    assert prv2.source_refs[0].startswith("SRC-25")
    assert "Tax Group" in prv2.source_refs[0]
    assert "SRC-25" in cal("CAL-3").source_refs


def test_ut20_cal3_window_boundaries_unchanged() -> None:
    assert _prv2_finding_message("2027-01-01", "CAL-3")[0] == "grace_period"
    assert _prv2_finding_message("2028-12-31", "CAL-3")[0] == "grace_period"
    assert _prv2_finding_message("2026-12-31", "CAL-3")[0] == "pass"
    assert _prv2_finding_message("2029-01-01", "CAL-3")[0] == "pass"


def test_ut20_excluded_invoice_finding_cites_the_provision_source_and_end_date() -> None:
    # Before C1 the text was the bare "grace period (PRV-2)", which named no legal basis.
    _, msg = _prv2_finding_message("2027-06-30", "CAL-3")
    assert msg is not None
    assert "PRV-2" in msg and "2028-12-31" in msg
    assert "SRC-25" in msg and "Tax Group" in msg
    _, old = _prv2_finding_message("2027-06-30", "CAL-2")
    assert old is not None and "SRC-02 §6.3.2.1" in old and "SRC-25" not in old


def test_ut20_rp1_fixture_suite_passes_under_cal3() -> None:
    assert run_suite(rp1(), rp1_cases(), cal("CAL-3").provisions) == []


def test_ut21_deadline_flag_reads_asp_status_only_never_data_status() -> None:
    # The data check cannot show whether a client will meet its appointment date: the
    # dashboard row carries no data status, and "past appoint-by without ASP" depends only
    # on the calendar date and the Reviewer-recorded ASP status.
    assert {f.name for f in dataclasses.fields(SortableRow)} == {
        "entity_id",
        "legal_name",
        "deadline",
        "asp_status",
    }
    c = cal("CAL-3")
    before = deadline_view(c, "SEG-S", date(2027, 3, 31))
    after = deadline_view(c, "SEG-S", date(2027, 4, 1))
    assert not overdue_without_asp(SortableRow("a", "a", before, "not_appointed"))
    assert overdue_without_asp(SortableRow("a", "a", after, "not_appointed"))
    assert not overdue_without_asp(SortableRow("a", "a", after, "appointed"))
    rows = [
        SortableRow("appointed", "appointed", after, "appointed"),
        SortableRow("open", "open", after, "not_appointed"),
    ]
    assert [r.entity_id for r in risk_sort(rows)] == ["open", "appointed"]
