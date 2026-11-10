"""Golden-fixture suite for a rule pack (TRD 8.4 step 1, IT-12).

A pack is published only when every case in its fixture file gives the expected
record-level outcome. Cases are synthetic (AGENTS section 7).
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from pintae_rules.calendar import Provision
from pintae_rules.engine import DatasetInput, EngineInput, Row, run
from pintae_rules.packs import RulePack, canonical_json


def build_input(case: Mapping[str, Any], provisions: Sequence[Provision] = ()) -> EngineInput:
    datasets: dict[str, DatasetInput | None] = {}
    for name in ("customers", "items", "invoices"):
        spec = (case.get("datasets") or {}).get(name)
        if spec is None:
            datasets[name] = None
            continue
        rows = []
        fields: dict[str, str] = {}
        for i, r in enumerate(spec.get("rows", []), start=2):
            rows.append(
                Row(
                    row_number=i,
                    values={k: (None if v is None else str(v)) for k, v in r.items()},
                    columns={k: k for k in r},
                    sheet=spec.get("sheet"),
                )
            )
            for k in r:
                fields[k] = "mapped"
        for k, v in (spec.get("fields") or {}).items():
            if v is None:
                fields.pop(k, None)
            else:
                fields[k] = v
        datasets[name] = DatasetInput(upload_id=f"fixture-{name}", rows=rows, field_status=fields)
    vmaps = {(k, s): t for k, s, t in case.get("value_maps", [])}
    return EngineInput(
        seller=case.get("seller", {}),
        datasets=datasets,
        value_maps=vmaps,
        segment=case.get("segment"),
        provisions=provisions,
    )


@dataclass(frozen=True)
class FixtureFailure:
    case: str
    rule: str
    record: str
    expected: str
    actual: str | None


def run_suite(
    pack: RulePack, cases: Sequence[Mapping[str, Any]], provisions: Sequence[Provision] = ()
) -> list[FixtureFailure]:
    failures: list[FixtureFailure] = []
    for case in cases:
        result = run(pack, build_input(case, provisions))
        for exp in case["expect"]:
            actual = result.outcome(exp["rule"], exp["record"], exp.get("dataset"))
            expected = exp["outcome"]
            if expected == "not_applied":
                if actual is not None:
                    failures.append(
                        FixtureFailure(case["name"], exp["rule"], exp["record"], expected, actual)
                    )
            elif actual != expected:
                failures.append(
                    FixtureFailure(case["name"], exp["rule"], exp["record"], expected, actual)
                )
    return failures


def suite_hash(pack: RulePack, cases: Sequence[Mapping[str, Any]]) -> bytes:
    """Reference to the fixture run: the pack hash it ran against plus the cases' hash."""
    return hashlib.sha256(pack.hash + canonical_json(list(cases))).digest()
