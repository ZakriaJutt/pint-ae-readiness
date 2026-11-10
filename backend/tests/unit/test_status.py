"""Status function (UT-11, UT-17) and dashboard risk sort."""

from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
from typing import Any

from pintae_rules.calendar import deadline_view
from pintae_rules.dashboard import SortableRow, risk_sort
from pintae_rules.engine import EngineResult
from pintae_rules.status import (
    Counts,
    EntityState,
    Status,
    StoredFinding,
    Versions,
    base_status,
    can_be_data_ready,
    effective_status,
    label,
    summarise,
)
from tests.helpers import cal, clean_case, customer, invoice_line, run_case

TODAY = date(2027, 2, 10)
FULL = EntityState(True, "SEG-S", frozenset({"customers", "items", "invoices"}), True)
V1 = Versions("RP-1", 1, {"customers": 1, "items": 1, "invoices": 1, "values": "d0"}, 1)


def stored(r: EngineResult) -> list[StoredFinding]:
    return [
        StoredFinding(f.fingerprint, f.dataset, f.record_key, f.severity, f.outcome)
        for f in r.findings
    ]


def in_scope(r: EngineResult) -> dict[str, int]:
    c = Counter(s.dataset for s in r.records if s.scope == "in_scope")
    return dict(c)


def status_of(
    case: dict[str, Any],
    *,
    approved_map: bool = True,
    approved: bool = False,
    exceptions: tuple[str, ...] = (),
    resolutions: dict[str, str] | None = None,
    entity: EntityState = FULL,
) -> tuple[Status, Counts]:
    r = run_case(case)
    fs = stored(r)
    if resolutions:
        fs = [
            StoredFinding(
                f.fingerprint,
                f.dataset,
                f.record_key,
                f.severity,
                f.outcome,
                resolutions.get(f.record_key) if f.outcome == "manual_review" else None,
            )
            for f in fs
        ]
    counts = summarise(fs, exceptions, in_scope(r))
    return base_status(
        entity, counts, mappings_approved=approved_map, reviewer_approved=approved
    ), counts


def test_ut11_failed_blocker_gives_gaps_open() -> None:
    c = clean_case()
    c["datasets"]["invoices"]["rows"] = [invoice_line(invoice_total="1.00")]
    assert status_of(c)[0] is Status.GAPS_OPEN


def test_ut11_buyer_trn_not_in_this_file_is_checks_incomplete_never_ready() -> None:
    c = clean_case()
    c["datasets"]["customers"]["rows"] = [
        customer(customer_id=f"C{i}", trn=None) for i in range(1, 4)
    ]
    c["datasets"]["customers"]["fields"] = {"trn": "absent", "tin": "absent"}
    c["datasets"]["invoices"]["rows"] = [invoice_line()]
    st, counts = status_of(c, approved=True)
    assert st is Status.CHECKS_INCOMPLETE
    assert counts.unchecked_blockers == 3
    assert counts.score_by_dataset["customers"]["score_percent"] == "0.0"
    assert not can_be_data_ready(counts, True)


def test_ut11_accepted_exception_gives_exceptions_open() -> None:
    c = clean_case()
    c["datasets"]["customers"]["rows"] = [customer(trn=None)]
    r = run_case(c)
    fp = next(f.fingerprint for f in r.findings if f.rule_code == "RC-07")
    st, counts = status_of(c, exceptions=(fp,), approved=True)
    assert st is Status.EXCEPTIONS_OPEN
    assert counts.accepted_exceptions == 1 and counts.failed_blockers == 0
    assert counts.score_by_dataset["customers"]["passed"] == 0  # an exception is not a pass


def test_ut11_clean_but_mapping_not_approved_is_review_pending() -> None:
    st, counts = status_of(clean_case(), approved_map=False, approved=True)
    assert st is Status.REVIEW_PENDING
    assert not can_be_data_ready(counts, False)


def test_ut11_clean_awaiting_review_then_approved() -> None:
    assert status_of(clean_case())[0] is Status.REVIEW_PENDING
    assert status_of(clean_case(), approved=True)[0] is Status.DATA_READY


def test_ut11_approved_then_pack_changed_is_stale() -> None:
    st, _ = status_of(clean_case(), approved=True)
    current = Versions("RP-2", 1, V1.mapping_versions, 1)
    eff, reasons = effective_status(st, V1, current, TODAY, TODAY)
    assert eff is Status.STALE and reasons == ["rule_pack_changed"]


def test_ut11_segment_unknown_with_zero_findings() -> None:
    e = EntityState(True, "SEG-U", FULL.datasets_present, True)
    assert status_of(clean_case(), entity=e, approved=True)[0] is Status.SEGMENT_NOT_CONFIRMED
    e = EntityState(True, None, FULL.datasets_present, True)
    assert status_of(clean_case(), entity=e, approved=True)[0] is Status.SEGMENT_NOT_CONFIRMED


def test_ut11_seller_address_unknown_is_checks_incomplete() -> None:
    c = clean_case()
    c["seller"]["address_line"] = "unknown"
    assert status_of(c, approved=True)[0] is Status.CHECKS_INCOMPLETE


def test_ut11_self_billed_before_and_after_reviewer() -> None:
    c = clean_case()
    c["datasets"]["invoices"]["rows"] = [
        invoice_line(),
        invoice_line(invoice_number="SB-1", document_type="389"),
        invoice_line(invoice_number="SB-2", document_type="389"),
    ]
    st, counts = status_of(c, approved=True)
    assert st is Status.CHECKS_INCOMPLETE and counts.unresolved_manual_reviews == 2
    st, counts = status_of(
        c, resolutions={"SB-1": "confirmed_self_billed", "SB-2": "confirmed_self_billed"}
    )
    assert st is Status.REVIEW_PENDING
    assert counts.not_assessed_self_billed == 2
    assert counts.score_by_dataset["invoices"]["in_scope"] == 1
    # "type corrected" still needs a re-run: it stays blocking.
    st, _ = status_of(c, resolutions={"SB-1": "type_corrected", "SB-2": "confirmed_self_billed"})
    assert st is Status.CHECKS_INCOMPLETE


def test_missing_dataset_is_data_incomplete() -> None:
    e = EntityState(True, "SEG-S", frozenset({"customers", "items"}), True)
    assert status_of(clean_case(), entity=e, approved=True)[0] is Status.DATA_INCOMPLETE
    e = EntityState(True, "SEG-S", FULL.datasets_present, False)
    assert status_of(clean_case(), entity=e, approved=True)[0] is Status.DATA_INCOMPLETE
    e = EntityState(False, "SEG-S", frozenset(), False)
    assert (
        base_status(e, None, mappings_approved=True, reviewer_approved=True) is Status.NOT_STARTED
    )


def test_ut17_45_days_then_46_with_no_job() -> None:
    newest = TODAY - timedelta(days=45)
    assert effective_status(Status.DATA_READY, V1, V1, newest, TODAY)[0] is Status.DATA_READY
    newest = TODAY - timedelta(days=46)
    eff, reasons = effective_status(Status.DATA_READY, V1, V1, newest, TODAY)
    assert eff is Status.STALE and reasons == ["data_older_than_45_days"]


def test_stale_does_not_hide_gaps() -> None:
    current = Versions("RP-2", 2, {}, 2)
    assert effective_status(Status.GAPS_OPEN, V1, current, TODAY, TODAY)[0] is Status.GAPS_OPEN


def test_mapping_or_profile_change_is_stale() -> None:
    m = Versions("RP-1", 1, {**V1.mapping_versions, "customers": 2}, 1)
    assert effective_status(Status.REVIEW_PENDING, V1, m, TODAY, TODAY)[0] is Status.STALE
    p = Versions("RP-1", 1, V1.mapping_versions, 2)
    assert effective_status(Status.EXCEPTIONS_OPEN, V1, p, TODAY, TODAY)[1] == ["profile_changed"]


def test_label_never_bare_ready() -> None:
    assert label(Status.DATA_READY, "RP-1") == "Data-ready (RP-1)"
    labels = {label(s) for s in Status}
    assert not any("compliant" in x.lower() for x in labels)
    assert "Ready" not in labels


def test_dashboard_order_e2e08_scenario() -> None:
    day = date(2027, 1, 15)
    c = cal()

    def row(eid: str, seg: str | None, asp: str, **kw: str) -> SortableRow:
        return SortableRow(eid, eid, deadline_view(c, seg, day, **kw), asp)  # type: ignore[arg-type]

    rows = [
        row("s-appointed", "SEG-S", "appointed"),
        row("s-open", "SEG-S", "not_appointed"),
        row("l-open", "SEG-L", "not_appointed"),
        row("u-open", "SEG-U", "not_appointed"),
        row("n-open", "SEG-N", "not_appointed", first_invoice_state="issued"),
    ]
    order = [r.entity_id for r in risk_sort(rows)]
    assert order == ["l-open", "u-open", "n-open", "s-open", "s-appointed"]
    from pintae_rules.dashboard import overdue_without_asp

    assert sum(overdue_without_asp(r) for r in rows) == 3
