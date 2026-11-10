"""Segment function and calendar (UT-10, UT-13, UT-16)."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from pintae_rules.calendar import deadline_view
from pintae_rules.dates import dubai_date, dubai_today
from pintae_rules.segment import SegmentFacts, classify
from tests.helpers import cal

TODAY = date(2026, 11, 11)


@pytest.mark.parametrize(
    ("facts", "segment", "appoint", "implement"),
    [
        (SegmentFacts("person", "ge_50m"), "SEG-L", date(2026, 10, 30), date(2027, 1, 1)),
        (SegmentFacts("person", "lt_50m"), "SEG-S", date(2027, 3, 31), date(2027, 7, 1)),
        (
            SegmentFacts("government_entity", "lt_50m"),
            "SEG-G",
            date(2027, 3, 31),
            date(2027, 10, 1),
        ),
        (
            SegmentFacts("government_entity", "unknown"),
            "SEG-G",
            date(2027, 3, 31),
            date(2027, 10, 1),
        ),
    ],
)
def test_ut10_fixed_segments(
    facts: SegmentFacts, segment: str, appoint: date, implement: date
) -> None:
    seg = classify(facts)
    assert seg == segment
    v = deadline_view(cal(), seg, TODAY)
    assert (v.governing_appoint_by, v.governing_implement_by) == (appoint, implement)
    assert v.calendar_code == "CAL-2"
    assert all(o.source_refs for o in v.outcomes)


def test_ut10_person_unknown_revenue_both_outcomes() -> None:
    seg = classify(SegmentFacts("person", "unknown"))
    assert seg == "SEG-U"
    v = deadline_view(cal(), seg, TODAY)
    assert not v.segment_confirmed
    got = {(o.segment, o.appoint_by, o.implement_by) for o in v.outcomes}
    assert got == {
        ("SEG-L", date(2026, 10, 30), date(2027, 1, 1)),
        ("SEG-S", date(2027, 3, 31), date(2027, 7, 1)),
    }
    assert v.governing_appoint_by == date(2026, 10, 30)
    assert v.appoint_by_passed
    assert any(o.label == "if Revenue is AED 50M or more" for o in v.outcomes)


def test_ut10_consumer_only_and_newly_established() -> None:
    assert classify(SegmentFacts("person", "lt_50m", b2c_only=True)) == "SEG-X"
    assert deadline_view(cal(), "SEG-X", TODAY).display == "Not subject"
    assert classify(SegmentFacts("person", "unknown", newly_established=True)) == "SEG-N"
    v = deadline_view(cal(), "SEG-N", TODAY, first_invoice_state="not_yet")
    assert v.display == "Before first invoice" and not v.appoint_by_passed
    v = deadline_view(cal(), "SEG-N", TODAY, first_invoice_state="issued")
    assert v.appoint_by_passed


def test_no_assessment_is_treated_as_unconfirmed() -> None:
    v = deadline_view(cal(), None, TODAY)
    assert v.segment == "SEG-U" and not v.segment_confirmed


def test_ut13_days_remaining_in_dubai() -> None:
    instant = datetime(2027, 3, 31, 21, 0, tzinfo=UTC)
    today = dubai_today(lambda: instant)
    assert today == date(2027, 4, 1)
    v = deadline_view(cal(), "SEG-S", today)
    assert v.display == "Passed" and v.days_remaining == -1
    # Same instant read in UTC would still be 31 March: the helper prevents that error.
    assert instant.date() == date(2027, 3, 31)
    with pytest.raises(ValueError, match="naive"):
        dubai_date(datetime(2027, 3, 31, 21, 0))


def test_ut16_cal2_seg_l_with_discrepancy() -> None:
    v = deadline_view(cal("CAL-2"), "SEG-L", TODAY)
    assert v.governing_appoint_by == date(2026, 10, 30)
    assert v.notes and "31 October 2026" in v.notes[0]
    old = deadline_view(cal("CAL-1"), "SEG-L", TODAY)
    assert old.governing_appoint_by == date(2026, 7, 31)
