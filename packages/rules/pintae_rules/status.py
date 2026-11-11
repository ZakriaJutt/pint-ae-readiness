"""The one status function (MH-08, AD-10, AD-11, T-3.2.3). Pure.

``summarise`` turns stored findings plus current exception and manual-review decisions
into counts; ``base_status`` applies PRD section 5's first-match table; ``effective_status``
derives Stale on every read from the run's pins, the current versions and today's date.
Nothing here reads a stored stale flag, because none exists.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from typing import Any

REQUIRED_DATASETS = ("customers", "items", "invoices")
STALE_AFTER_DAYS = 45  # [A] PRD section 5


class Status(StrEnum):
    NOT_STARTED = "not_started"
    SEGMENT_NOT_CONFIRMED = "segment_not_confirmed"
    DATA_INCOMPLETE = "data_incomplete"
    GAPS_OPEN = "gaps_open"
    CHECKS_INCOMPLETE = "checks_incomplete"
    EXCEPTIONS_OPEN = "exceptions_open"
    REVIEW_PENDING = "review_pending"
    DATA_READY = "data_ready"
    STALE = "stale"


LABELS = {
    Status.NOT_STARTED: "Not started",
    Status.SEGMENT_NOT_CONFIRMED: "Segment not confirmed",
    Status.DATA_INCOMPLETE: "Data incomplete",
    Status.GAPS_OPEN: "Gaps open",
    Status.CHECKS_INCOMPLETE: "Checks incomplete",
    Status.EXCEPTIONS_OPEN: "Exceptions open",
    Status.REVIEW_PENDING: "Review pending",
    Status.DATA_READY: "Data-ready",
    Status.STALE: "Stale",
}

# Stale replaces statuses 6 to 8 only (PRD section 5).
STALE_REPLACES = frozenset({Status.EXCEPTIONS_OPEN, Status.REVIEW_PENDING, Status.DATA_READY})


def label(status: Status, pack_code: str | None = None) -> str:
    """Display label. "Data-ready" is always shown with its pack version."""
    if status is Status.DATA_READY:
        return f"Data-ready ({pack_code})" if pack_code else "Data-ready"
    return LABELS[status]


@dataclass(frozen=True)
class StoredFinding:
    """The fields of a stored finding the status function needs."""

    fingerprint: str
    dataset: str
    record_key: str
    severity: str  # blocker | warning
    outcome: str  # fail | not_checked | manual_review | out_of_scope | grace_period
    review_resolution: str | None = None  # confirmed_self_billed | type_corrected


@dataclass(frozen=True)
class Counts:
    failed_blockers: int
    unchecked_blockers: int
    unresolved_manual_reviews: int
    not_assessed_self_billed: int
    accepted_exceptions: int
    score_by_dataset: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    # Required datasets that were mapped but had no data rows (B1-002): never "no findings".
    empty_datasets: tuple[str, ...] = ()


def summarise(
    findings: Iterable[StoredFinding],
    accepted_exception_fingerprints: Iterable[str],
    in_scope_at_run: Mapping[str, int],
    records_at_run: Mapping[str, int] | None = None,
) -> Counts:
    """Counts for the status table.

    * an accepted exception moves a failed blocker into ``accepted_exceptions``: it is
      never a pass;
    * a ``not_checked`` blocker is always counted (exceptions cannot attach to it);
    * an unresolved ``manual_review`` record blocks; one confirmed self-billed leaves the
      denominator and is counted as "not assessed"; ``type_corrected`` stays blocking
      until a re-run checks it normally.
    """
    accepted = set(accepted_exception_fingerprints)
    items = list(findings)
    self_billed = {
        (f.dataset, f.record_key)
        for f in items
        if f.outcome == "manual_review" and f.review_resolution == "confirmed_self_billed"
    }
    failed = unchecked = manual = excepted = 0
    blocking_records: dict[str, set[str]] = {}
    for f in items:
        rec = (f.dataset, f.record_key)
        if rec in self_billed:
            continue
        if f.outcome == "manual_review":
            manual += 1
            blocking_records.setdefault(f.dataset, set()).add(f.record_key)
            continue
        if f.severity != "blocker":
            continue
        if f.outcome == "fail":
            if f.fingerprint in accepted:
                excepted += 1
            else:
                failed += 1
            blocking_records.setdefault(f.dataset, set()).add(f.record_key)
        elif f.outcome == "not_checked":
            unchecked += 1
            blocking_records.setdefault(f.dataset, set()).add(f.record_key)
    removed: dict[str, int] = {}
    for ds, _key in self_billed:
        removed[ds] = removed.get(ds, 0) + 1
    scores: dict[str, dict[str, Any]] = {}
    for ds, n in sorted(in_scope_at_run.items()):
        in_scope = max(n - removed.get(ds, 0), 0)
        passed = max(in_scope - len(blocking_records.get(ds, set())), 0)
        score = (
            (Decimal(passed) / Decimal(in_scope) * 100).quantize(Decimal("0.1"), ROUND_HALF_UP)
            if in_scope
            else None
        )
        scores[ds] = {
            "in_scope_at_run": n,
            "in_scope": in_scope,
            "passed": passed,
            "score_percent": str(score) if score is not None else None,
        }
    empty: tuple[str, ...] = ()
    if records_at_run is not None:
        empty = tuple(ds for ds in REQUIRED_DATASETS if records_at_run.get(ds, 0) == 0)
    return Counts(failed, unchecked, manual, len(self_billed), excepted, scores, empty)


@dataclass(frozen=True)
class EntityState:
    """Current facts about the entity, read now (not from the run)."""

    has_upload: bool
    approved_segment: str | None  # None when no approved assessment
    datasets_present: frozenset[str]
    seller_profile_present: bool


def base_status(
    entity: EntityState,
    counts: Counts | None,
    *,
    mappings_approved: bool,
    reviewer_approved: bool,
) -> Status:
    """PRD section 5, first matching row wins."""
    if not entity.has_upload:
        return Status.NOT_STARTED
    if entity.approved_segment is None or entity.approved_segment == "SEG-U":
        return Status.SEGMENT_NOT_CONFIRMED
    if (
        not set(REQUIRED_DATASETS) <= entity.datasets_present
        or not entity.seller_profile_present
        or counts is None
    ):
        return Status.DATA_INCOMPLETE
    if counts.failed_blockers > 0:
        return Status.GAPS_OPEN
    if (
        counts.unchecked_blockers > 0
        or counts.unresolved_manual_reviews > 0
        or counts.empty_datasets
    ):
        return Status.CHECKS_INCOMPLETE
    if counts.accepted_exceptions > 0:
        return Status.EXCEPTIONS_OPEN
    if not mappings_approved or not reviewer_approved:
        return Status.REVIEW_PENDING
    return Status.DATA_READY


@dataclass(frozen=True)
class Versions:
    """Version identifiers a result depends on. Compared field by field."""

    rule_pack: str | None
    segment_version: int | None
    mapping_versions: Mapping[str, Any]  # dataset -> mapping version id; plus value-map digest
    profile_version: int | None
    # B1-001: provisions (PRV-2) come from the calendar, so a result depends on it.
    calendar_version: str | None = None
    # B1-005: the newest live upload per dataset, whatever its parse state.
    uploads: Mapping[str, str] = field(default_factory=dict)


def stale_reasons(
    pinned: Versions, current: Versions, newest_data_on: date, today: date
) -> list[str]:
    reasons: list[str] = []
    if pinned.rule_pack != current.rule_pack:
        reasons.append("rule_pack_changed")
    if pinned.segment_version != current.segment_version:
        reasons.append("segment_changed")
    if dict(pinned.mapping_versions) != dict(current.mapping_versions):
        reasons.append("mapping_changed")
    if pinned.profile_version != current.profile_version:
        reasons.append("profile_changed")
    if pinned.calendar_version != current.calendar_version:
        reasons.append("calendar_changed")
    if dict(pinned.uploads) != dict(current.uploads):
        reasons.append("upload_changed")
    if (today - newest_data_on).days > STALE_AFTER_DAYS:
        reasons.append("data_older_than_45_days")
    return reasons


def effective_status(
    base: Status, pinned: Versions, current: Versions, newest_data_on: date, today: date
) -> tuple[Status, list[str]]:
    """Derived on every read (AD-11). Returns (status, stale reasons)."""
    reasons = stale_reasons(pinned, current, newest_data_on, today)
    if reasons and base in STALE_REPLACES:
        return (Status.STALE, reasons)
    return (base, reasons)


def can_be_data_ready(counts: Counts, mappings_approved: bool) -> bool:
    """The same invariant the database CHECK on readiness_snapshots enforces."""
    return (
        counts.failed_blockers == 0
        and counts.unchecked_blockers == 0
        and counts.unresolved_manual_reviews == 0
        and counts.accepted_exceptions == 0
        and not counts.empty_datasets
        and mappings_approved
    )
