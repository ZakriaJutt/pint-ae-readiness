"""The one date helper: legal dates are calendar dates in Asia/Dubai (AGENTS section 4, UT-13)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

DUBAI = ZoneInfo("Asia/Dubai")

Clock = Callable[[], datetime]


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


def dubai_date(instant: datetime) -> date:
    """Calendar date in Dubai for an aware instant. Naive datetimes are refused."""
    if instant.tzinfo is None:
        raise ValueError("naive datetime: a time zone is required")
    return instant.astimezone(DUBAI).date()


def dubai_today(clock: Clock = utc_now) -> date:
    return dubai_date(clock())


def days_between(start: date, end: date) -> int:
    """Exact calendar-day difference end - start."""
    return (end - start).days
