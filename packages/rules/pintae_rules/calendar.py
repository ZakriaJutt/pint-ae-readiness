"""Calendar lookup (MH-03, UT-10, UT-13, UT-16). The only place dates per segment are read.

Dates come from a calendar version (data), never from code or from an old result.
SEG-U shows both candidate outcomes and is governed by the earliest one.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from datetime import date
from typing import Any

from pintae_rules.dates import days_between
from pintae_rules.segment import BOUNDARY_FLAG, BOUNDARY_NOTE, Segment


@dataclass(frozen=True)
class CalendarRule:
    segment: str
    deadline_basis: str  # fixed_date | before_first_invoice | not_subject | earliest_of_candidates
    appoint_by: date | None = None
    implement_by: date | None = None
    candidate_segments: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()
    note: str | None = None
    discrepancy: str | None = None


@dataclass(frozen=True)
class Provision:
    code: str
    kind: str
    applies_from: date | None
    applies_to: date | None
    selector: Mapping[str, Any]
    effect: str
    rule_code: str | None
    source_refs: tuple[str, ...]

    def covers(self, on: date) -> bool:
        if self.applies_from is not None and on < self.applies_from:
            return False
        return not (self.applies_to is not None and on > self.applies_to)


@dataclass(frozen=True)
class Calendar:
    code: str
    basis: str
    rules: Mapping[str, CalendarRule]
    provisions: tuple[Provision, ...] = ()
    source_refs: tuple[str, ...] = ()

    def rule(self, segment: str) -> CalendarRule:
        try:
            return self.rules[segment]
        except KeyError as exc:
            raise KeyError(f"{self.code} has no rule for {segment}") from exc


def _d(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def calendar_from_data(data: Mapping[str, Any]) -> Calendar:
    rules = {
        r["segment"]: CalendarRule(
            segment=r["segment"],
            deadline_basis=r["deadline_basis"],
            appoint_by=_d(r.get("appoint_by")),
            implement_by=_d(r.get("implement_by")),
            candidate_segments=tuple(r.get("candidate_segments") or ()),
            source_refs=tuple(r.get("source_refs") or ()),
            note=r.get("note"),
            discrepancy=r.get("discrepancy"),
        )
        for r in data["rules"]
    }
    provisions = tuple(
        Provision(
            code=p["code"],
            kind=p["kind"],
            applies_from=_d(p.get("applies_from")),
            applies_to=_d(p.get("applies_to")),
            selector=p.get("selector") or {},
            effect=p["effect"],
            rule_code=p.get("rule_code"),
            source_refs=tuple(p.get("source_refs") or ()),
        )
        for p in data.get("provisions", [])
    )
    return Calendar(
        code=data["code"],
        basis=data["basis"],
        rules=rules,
        provisions=provisions,
        source_refs=tuple(data.get("source_refs") or ()),
    )


@dataclass(frozen=True)
class Outcome:
    segment: str
    appoint_by: date | None
    implement_by: date | None
    source_refs: tuple[str, ...]
    discrepancy: str | None = None
    label: str | None = None


@dataclass(frozen=True)
class DeadlineView:
    """What a dashboard row or report prints for one entity on one day."""

    segment: str
    calendar_code: str
    basis: str
    outcomes: tuple[Outcome, ...]
    governing_appoint_by: date | None
    governing_implement_by: date | None
    days_remaining: int | None  # to the governing appoint-by date, in Asia/Dubai days
    appoint_by_passed: bool
    display: str  # e.g. "31 days", "Due today", "Passed", "Before first invoice", "Not subject"
    segment_confirmed: bool
    notes: tuple[str, ...] = field(default_factory=tuple)
    flags: tuple[str, ...] = field(default_factory=tuple)


def _fmt_days(days: int) -> str:
    if days < 0:
        return "Passed"
    if days == 0:
        return "Due today"
    return f"{days} day" if days == 1 else f"{days} days"


def deadline_view(
    calendar: Calendar,
    segment: str | None,
    today: date,
    *,
    first_invoice_state: str | None = None,
    first_invoice_on: date | None = None,
    revenue_band: str | None = None,
    earliest_invoice_on: date | None = None,
) -> DeadlineView:
    """Deadlines for a segment on ``today`` (a Dubai calendar date from ``dates.dubai_today``).

    ``segment=None`` (no assessment at all) is treated exactly like SEG-U.
    """
    seg = segment or Segment.U.value
    rule = calendar.rule(seg)
    confirmed = segment is not None and seg != Segment.U.value

    if rule.deadline_basis == "fixed_date":
        out = Outcome(seg, rule.appoint_by, rule.implement_by, rule.source_refs, rule.discrepancy)
        return _fixed(calendar, seg, (out,), today, confirmed)

    if rule.deadline_basis == "earliest_of_candidates":
        outs: list[Outcome] = []
        for cand in rule.candidate_segments:
            c = calendar.rule(cand)
            label = (
                "if Revenue is AED 50M or more"
                if cand == Segment.L.value
                else "if Revenue is below AED 50M"
                if cand == Segment.S.value
                else None
            )
            outs.append(
                Outcome(cand, c.appoint_by, c.implement_by, c.source_refs, c.discrepancy, label)
            )
        view = _fixed(calendar, seg, tuple(outs), today, confirmed)
        if revenue_band == "eq_50m":
            view = replace(view, notes=(*view.notes, BOUNDARY_NOTE), flags=(BOUNDARY_FLAG,))
        return view

    if rule.deadline_basis == "before_first_invoice":
        # B1-010: an unknown first-invoice state shows its worst case: the date is needed
        # and the row sorts as overdue until the Reviewer records it.
        needs_date = first_invoice_on is None and first_invoice_state in (None, "unknown")
        # B1-010: uploaded invoices dated on or before today show the entity has already
        # issued invoices, whatever the recorded state: flagged and treated as passed.
        already_invoicing = (
            first_invoice_state != "issued"
            and earliest_invoice_on is not None
            and earliest_invoice_on <= today
        )
        passed = (
            first_invoice_state == "issued"
            or (first_invoice_on is not None and first_invoice_on <= today)
            or needs_date
            or already_invoicing
        )
        flags: tuple[str, ...] = ()
        if already_invoicing:
            display = "Passed: uploaded invoices are already dated"
            flags = ("invoices_dated_before_today",)
        elif needs_date:
            display = "First invoice date needed"
            flags = ("first_invoice_date_needed",)
        else:
            display = "Passed" if passed else "Before first invoice"
        return DeadlineView(
            segment=seg,
            calendar_code=calendar.code,
            basis=rule.deadline_basis,
            outcomes=(Outcome(seg, None, None, rule.source_refs),),
            governing_appoint_by=first_invoice_on,
            governing_implement_by=first_invoice_on,
            days_remaining=None
            if first_invoice_on is None
            else days_between(today, first_invoice_on),
            appoint_by_passed=passed,
            display=display,
            segment_confirmed=confirmed,
            flags=flags,
        )

    if rule.deadline_basis == "not_subject":
        return DeadlineView(
            segment=seg,
            calendar_code=calendar.code,
            basis=rule.deadline_basis,
            outcomes=(Outcome(seg, None, None, rule.source_refs),),
            governing_appoint_by=None,
            governing_implement_by=None,
            days_remaining=None,
            appoint_by_passed=False,
            display="Not subject",
            segment_confirmed=confirmed,
        )

    raise ValueError(f"unknown deadline basis {rule.deadline_basis!r}")


def _fixed(
    calendar: Calendar, seg: str, outs: tuple[Outcome, ...], today: date, confirmed: bool
) -> DeadlineView:
    appoints = [o.appoint_by for o in outs if o.appoint_by is not None]
    implements = [o.implement_by for o in outs if o.implement_by is not None]
    gov_a = min(appoints) if appoints else None
    gov_i = min(implements) if implements else None
    days = days_between(today, gov_a) if gov_a is not None else None
    notes = tuple(o.discrepancy for o in outs if o.discrepancy)
    return DeadlineView(
        segment=seg,
        calendar_code=calendar.code,
        basis=calendar.rule(seg).deadline_basis,
        outcomes=outs,
        governing_appoint_by=gov_a,
        governing_implement_by=gov_i,
        days_remaining=days,
        appoint_by_passed=days is not None and days < 0,
        display=_fmt_days(days) if days is not None else "No date",
        segment_confirmed=confirmed,
        notes=notes,
    )
