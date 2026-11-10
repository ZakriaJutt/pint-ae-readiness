"""Segment function (MH-02, UT-10). Pure; no default decides a segment.

Definitions: Decision.md section 3. Revenue may be ``unknown``; that gives SEG-U for a
Person, never a guessed band.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Segment(StrEnum):
    L = "SEG-L"
    S = "SEG-S"
    G = "SEG-G"
    N = "SEG-N"
    X = "SEG-X"
    U = "SEG-U"


ENTITY_TYPES = ("person", "government_entity")
REVENUE_BANDS = ("ge_50m", "lt_50m", "unknown")


@dataclass(frozen=True)
class SegmentFacts:
    entity_type: str  # person | government_entity
    revenue_band: str = "unknown"  # ge_50m | lt_50m | unknown
    newly_established: bool = False
    b2c_only: bool = False


def classify(facts: SegmentFacts) -> Segment:
    if facts.entity_type not in ENTITY_TYPES:
        raise ValueError(f"unknown entity_type {facts.entity_type!r}")
    if facts.revenue_band not in REVENUE_BANDS:
        raise ValueError(f"unknown revenue_band {facts.revenue_band!r}")
    if facts.entity_type == "government_entity":
        # Government entities are SEG-G whatever their Revenue (Decision section 3).
        return Segment.G
    if facts.b2c_only:
        return Segment.X
    if facts.newly_established:
        return Segment.N
    if facts.revenue_band == "ge_50m":
        return Segment.L
    if facts.revenue_band == "lt_50m":
        return Segment.S
    return Segment.U
