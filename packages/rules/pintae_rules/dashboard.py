"""Risk sort for the multi-client view (MH-09). Pure.

Default order: entities past their governing appoint-by date without an ASP appointment
first (SEG-U by its earliest possible date, SEG-N once its first invoice is issued), then
not appointed before appointed, then by days remaining.
"""

from __future__ import annotations

from dataclasses import dataclass

from pintae_rules.calendar import DeadlineView

NOT_APPOINTED = "not_appointed"


@dataclass(frozen=True)
class SortableRow:
    entity_id: str
    legal_name: str
    deadline: DeadlineView
    asp_status: str  # not_appointed | appointed | onboarded | live


def overdue_without_asp(row: SortableRow) -> bool:
    return row.deadline.appoint_by_passed and row.asp_status == NOT_APPOINTED


def risk_key(row: SortableRow) -> tuple[int, int, int, int, str, str]:
    days = row.deadline.days_remaining
    return (
        0 if overdue_without_asp(row) else 1,
        0 if row.asp_status == NOT_APPOINTED else 1,
        days if days is not None else 10**6,
        0 if row.deadline.segment_confirmed else 1,
        row.legal_name.casefold(),
        row.entity_id,
    )


def risk_sort(rows: list[SortableRow]) -> list[SortableRow]:
    return sorted(rows, key=risk_key)
