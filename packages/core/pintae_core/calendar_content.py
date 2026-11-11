"""Calendar content from its child rows (B1-012, B1-014).

``calendar_rows_data`` rebuilds a calendar version's data from ``calendar_rules`` and
``provisions``; the loader compares it with the stored, hashed ``content``.
``derive_missing_content`` fills ``content`` once for calendar versions published before
migration 0004, which added the column (B1-014). It is called only from migrations, writes
only rows whose ``content`` is NULL, and is idempotent and resumable.

For each such row:
- ``publication``: the shipped calendar file with the same code hashes to the stored
  ``content_hash`` and describes exactly the stored rows; it becomes the content, and the
  hash is unchanged.
- ``derived_from_rows``: otherwise the rows (which is what every read used before 0004)
  form a valid calendar whose every rule cites a source; the rebuilt data becomes the
  content and its hash the ``content_hash``. The ``publications`` row keeps the hash that
  was confirmed at publication.
- ``legacy_unverified``: neither holds. ``content`` stays NULL; no run can newly pin the
  version, and results pinned to it read as Stale (``calendar_legacy_unverified``).
"""

from __future__ import annotations

import json
from dataclasses import replace
from typing import Any

from sqlalchemy import text

from pintae_rules.calendar import Calendar, calendar_from_data
from pintae_rules.packs import content_hash

ORIGINS = ("publication", "derived_from_rows", "legacy_unverified")


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


def classify(
    rows_data: dict[str, Any], stored_hash: bytes
) -> tuple[str, dict[str, Any] | None, bytes]:
    """(origin, content, content_hash) for one calendar version whose content is NULL."""
    try:
        rows_cal = calendar_from_data(rows_data)
    except (KeyError, TypeError, ValueError):
        return "legacy_unverified", None, stored_hash
    if not rows_data["rules"]:
        return "legacy_unverified", None, stored_hash
    shipped = _shipped(rows_data["code"])
    if shipped is not None and content_hash(shipped) == stored_hash:
        try:
            if same_calendar(calendar_from_data(shipped), rows_cal):
                return "publication", shipped, stored_hash
        except (KeyError, TypeError, ValueError):
            pass
    if all(r.source_refs for r in rows_cal.rules.values()):
        return "derived_from_rows", rows_data, content_hash(rows_data)
    return "legacy_unverified", None, stored_hash


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
        origin, content, digest = classify(data, bytes(r.content_hash))
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
