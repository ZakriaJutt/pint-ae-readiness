"""Calendar content from its child rows (B1-012, B1-014).

``calendar_rows_data`` rebuilds a calendar version's data from ``calendar_rules`` and
``provisions``; the loader compares it with the stored, hashed ``content``.
``derive_missing_content`` fills ``content`` once for calendar versions published before
migration 0004, which added the column (B1-014). It is called only from migrations, writes
only rows whose ``content`` is NULL, and is idempotent and resumable.

For each such row (B1-015: the database's own rows cannot vouch for themselves):
- ``publication``: the calendar file shipped in the repository for that version code is the
  one the version was published from (its ``content_hash`` equals both the stored hash and
  the ``publications`` row) and the calendar rebuilt from the stored rows is identical to it
  in canonical form and hash. The file becomes the content; the hash is unchanged.
- ``legacy_unverified``: anything else (no shipped file, a different hash, or rows that
  differ, for example a deadline or provision edited before 0004). ``content`` stays NULL;
  no run newly pins the version, results pinned to it read Stale
  (``calendar_legacy_unverified``), loading it returns 409, and an operator publishes a new
  version from the shipped definition. Rule packs never needed this: ``rule_packs.content``
  has been NOT NULL and hashed since migration 0001.

``derived_from_rows`` was produced by an earlier draft of this step (B1-015); loaders treat
any such row as ``legacy_unverified``, and this step no longer produces it.
"""

from __future__ import annotations

import json
from dataclasses import replace
from typing import Any

from sqlalchemy import text

from pintae_rules.calendar import Calendar, calendar_from_data
from pintae_rules.packs import content_hash

ORIGINS = ("publication", "derived_from_rows", "legacy_unverified")
# Origins a loader refuses to serve (B1-015).
UNVERIFIED = frozenset({"derived_from_rows", "legacy_unverified"})


def _iso(v: Any) -> str | None:
    return v.isoformat() if v is not None else None


def calendar_rows_data(
    ex: Any, version_id: Any, code: str, basis: str, source_refs: dict[str, Any]
) -> dict[str, Any]:
    """``ex`` is a Session or a Connection."""
    rules = ex.execute(
        text(
            "SELECT segment, deadline_basis, appoint_by, implement_by, candidate_segments,"
            " source_refs, note, discrepancy FROM calendar_rules"
            " WHERE calendar_version_id = :v ORDER BY segment"
        ),
        {"v": version_id},
    ).all()
    provs = ex.execute(
        text(
            "SELECT code, kind, applies_from, applies_to, selector, effect, rule_code,"
            " source_refs FROM provisions WHERE calendar_version_id = :v ORDER BY code"
        ),
        {"v": version_id},
    ).all()
    return {
        "code": code,
        "basis": basis,
        "source_refs": list(source_refs.get("refs", [])),
        "rules": [
            {
                "segment": r.segment,
                "deadline_basis": r.deadline_basis,
                "appoint_by": _iso(r.appoint_by),
                "implement_by": _iso(r.implement_by),
                "candidate_segments": list(r.candidate_segments or []),
                "source_refs": list(r.source_refs.get("refs", [])),
                "note": r.note,
                "discrepancy": r.discrepancy,
            }
            for r in rules
        ],
        "provisions": [
            {
                "code": p.code,
                "kind": p.kind,
                "applies_from": _iso(p.applies_from),
                "applies_to": _iso(p.applies_to),
                "selector": p.selector,
                "effect": p.effect,
                "rule_code": p.rule_code,
                "source_refs": list(p.source_refs.get("refs", [])),
            }
            for p in provs
        ],
    }


def same_calendar(a: Calendar, b: Calendar) -> bool:
    def norm(c: Calendar) -> Calendar:
        return replace(c, provisions=tuple(sorted(c.provisions, key=lambda p: p.code)))

    return norm(a) == norm(b)


def _shipped(code: str) -> dict[str, Any] | None:
    try:
        from pintae_rulepacks import load_data

        return load_data(code)
    except (FileNotFoundError, ValueError):
        return None


def canonical_calendar(data: dict[str, Any]) -> dict[str, Any]:
    """One canonical form for a calendar, whatever extra keys a file carries: the fields the
    application reads, provisions in code order."""
    cal = calendar_from_data(data)
    return {
        "code": cal.code,
        "basis": cal.basis,
        "source_refs": list(cal.source_refs),
        "rules": [
            {
                "segment": r.segment,
                "deadline_basis": r.deadline_basis,
                "appoint_by": _iso(r.appoint_by),
                "implement_by": _iso(r.implement_by),
                "candidate_segments": list(r.candidate_segments),
                "source_refs": list(r.source_refs),
                "note": r.note,
                "discrepancy": r.discrepancy,
            }
            for _, r in sorted(cal.rules.items())
        ],
        "provisions": [
            {
                "code": p.code,
                "kind": p.kind,
                "applies_from": _iso(p.applies_from),
                "applies_to": _iso(p.applies_to),
                "selector": dict(p.selector),
                "effect": p.effect,
                "rule_code": p.rule_code,
                "source_refs": list(p.source_refs),
            }
            for p in sorted(cal.provisions, key=lambda p: p.code)
        ],
    }


def classify(
    rows_data: dict[str, Any], stored_hash: bytes, published_hashes: set[bytes]
) -> tuple[str, dict[str, Any] | None, bytes]:
    """(origin, content, content_hash) for one calendar version whose content is NULL."""
    shipped = _shipped(rows_data["code"])
    if shipped is None:
        return "legacy_unverified", None, stored_hash
    digest = content_hash(shipped)
    if digest != stored_hash or (published_hashes and published_hashes != {digest}):
        return "legacy_unverified", None, stored_hash
    try:
        rows_form, shipped_form = canonical_calendar(rows_data), canonical_calendar(shipped)
    except (KeyError, TypeError, ValueError):
        return "legacy_unverified", None, stored_hash
    if content_hash(rows_form) != content_hash(shipped_form):
        return "legacy_unverified", None, stored_hash
    return "publication", shipped, stored_hash


def derive_missing_content(conn: Any) -> dict[str, str]:
    """Migration step (B1-014). The caller suspends the calendar_versions guard around it."""
    out: dict[str, str] = {}
    rows = conn.execute(
        text(
            "SELECT id, code, basis, source_refs, content_hash FROM calendar_versions"
            " WHERE content IS NULL AND content_origin IS DISTINCT FROM 'legacy_unverified'"
            " ORDER BY code FOR UPDATE"
        )
    ).all()
    for r in rows:
        data = calendar_rows_data(conn, r.id, r.code, r.basis, r.source_refs)
        published = {
            bytes(h)
            for h in conn.execute(
                text(
                    "SELECT content_hash FROM publications"
                    " WHERE object_type = 'calendar_version' AND object_id = :i"
                ),
                {"i": r.id},
            ).scalars()
        }
        origin, content, digest = classify(data, bytes(r.content_hash), published)
        conn.execute(
            text(
                "UPDATE calendar_versions SET content = CAST(:c AS jsonb), content_hash = :h,"
                " content_origin = :o WHERE id = :i AND content IS NULL"
            ),
            {
                "c": json.dumps(content) if content is not None else None,
                "h": digest,
                "o": origin,
                "i": r.id,
            },
        )
        out[r.code] = origin
    return out
