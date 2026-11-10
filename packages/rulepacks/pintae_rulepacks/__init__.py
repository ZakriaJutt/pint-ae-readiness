"""Versioned rule-pack and calendar data files (AD-07). Immutable after publication."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).parent / "data"
FIXTURE_DIR = Path(__file__).parent / "fixtures"


def load_data(code: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((DATA_DIR / f"{code}.json").read_text(encoding="utf-8"))
    return data


def fixture_path(code: str) -> Path:
    return FIXTURE_DIR / f"{code}.fixtures.json"
