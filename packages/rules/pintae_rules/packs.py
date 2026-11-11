"""Rule packs as versioned data (AD-07). Loading, hashing and selection by effective date."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from typing import Any

REQUIRED_PACK_KEYS = ("code", "basis", "released_on", "effective_label", "source_refs", "rules")
REQUIRED_RULE_KEYS = ("code", "severity", "evaluator", "applies_to", "source_refs", "description")


class PackError(ValueError):
    pass


def canonical_json(data: Any) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def content_hash(data: Mapping[str, Any]) -> bytes:
    return hashlib.sha256(canonical_json(data)).digest()


@dataclass(frozen=True)
class Rule:
    code: str
    severity: str  # blocker | warning
    evaluator: str
    applies_to: Mapping[str, Any]
    fields: tuple[str, ...]
    source_refs: tuple[str, ...]
    description: str
    valid_from: date | None = None
    valid_to: date | None = None
    params: Mapping[str, Any] | None = None

    @property
    def datasets(self) -> tuple[str, ...]:
        ds = self.applies_to.get("dataset")
        if isinstance(ds, str):
            return (ds,)
        return tuple(ds or ())

    def param(self, key: str, default: Any = None) -> Any:
        return (self.params or {}).get(key, default)


@dataclass(frozen=True)
class RulePack:
    code: str
    basis: str
    released_on: date
    effective_from: date | None
    effective_label: str
    source_refs: tuple[str, ...]
    rules: tuple[Rule, ...]
    code_lists: Mapping[str, Sequence[str]]
    code_shapes: Mapping[str, str]
    value_mapping_kinds: Mapping[str, str]
    patterns: Mapping[str, str]
    date_formats: tuple[str, ...]
    segments: tuple[str, ...]
    hash: bytes
    aliases: Mapping[str, Mapping[str, str]] = field(default_factory=dict)

    @property
    def starts_on(self) -> date:
        """Effective date; when none is published the release date is used [A] (Decision §3)."""
        return self.effective_from or self.released_on

    def rule(self, code: str) -> Rule:
        for r in self.rules:
            if r.code == code:
                return r
        raise KeyError(code)


def validate_pack_data(data: Mapping[str, Any]) -> None:
    missing = [k for k in REQUIRED_PACK_KEYS if k not in data]
    if missing:
        raise PackError(f"pack missing keys: {missing}")
    if not data["source_refs"]:
        raise PackError("pack has no source references")
    seen: set[str] = set()
    for r in data["rules"]:
        miss = [k for k in REQUIRED_RULE_KEYS if k not in r]
        if miss:
            raise PackError(f"rule {r.get('code')} missing keys: {miss}")
        if not r["source_refs"]:
            raise PackError(f"rule {r['code']} has no source references")
        if r["severity"] not in ("blocker", "warning"):
            raise PackError(f"rule {r['code']} has severity {r['severity']!r}")
        if r["code"] in seen:
            raise PackError(f"duplicate rule code {r['code']}")
        seen.add(r["code"])


def _d(v: str | None) -> date | None:
    return date.fromisoformat(v) if v else None


def pack_from_data(data: Mapping[str, Any]) -> RulePack:
    validate_pack_data(data)
    rules = tuple(
        Rule(
            code=r["code"],
            severity=r["severity"],
            evaluator=r["evaluator"],
            applies_to=r["applies_to"],
            fields=tuple(r.get("fields") or ()),
            source_refs=tuple(r["source_refs"]),
            description=r["description"],
            valid_from=_d(r.get("valid_from")),
            valid_to=_d(r.get("valid_to")),
            params=r.get("params"),
        )
        for r in data["rules"]
    )
    released = _d(data["released_on"])
    assert released is not None
    return RulePack(
        code=data["code"],
        basis=data["basis"],
        released_on=released,
        effective_from=_d(data.get("effective_from")),
        effective_label=data["effective_label"],
        source_refs=tuple(data["source_refs"]),
        rules=rules,
        code_lists=data.get("code_lists", {}),
        code_shapes=data.get("code_shapes", {}),
        value_mapping_kinds=data.get("value_mapping_kinds", {}),
        patterns=data.get("patterns", {}),
        date_formats=tuple(data.get("date_formats", ("%Y-%m-%d",))),
        segments=tuple(data.get("segments", ())),
        hash=content_hash(data),
        aliases=data.get("aliases", {}),
    )


@dataclass(frozen=True)
class PackRef:
    code: str
    starts_on: date
    published_order: int  # larger is later


def select_current(packs: Sequence[PackRef], today: date) -> PackRef | None:
    """The pack in force on ``today``: latest effective date not after today, then latest published."""
    candidates = [p for p in packs if p.starts_on <= today]
    if not candidates:
        return None
    return max(candidates, key=lambda p: (p.starts_on, p.published_order))
