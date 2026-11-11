"""Rule-pack and calendar publication (TRD 8.4, T-3.2.4, IT-12).

Two steps, stated once: (1) the fixture suite runs against the file and records its hash;
(2) a vendor publisher confirms the same hash. With one founder these are one person. The
TOTP confirmation of step 2 is out of B1 scope (no sign-in yet): the publisher is named by id.

Runs on the owner connection (global tables are read-only to the application role). Staleness
needs no job: every read compares pins with the published versions.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import Engine, select, text
from sqlalchemy.orm import Session

from pintae_core.models import (
    CalendarRuleRow,
    CalendarVersion,
    ProvisionRow,
    Publication,
    RulePackRow,
    RuleRow,
    VendorUser,
)
from pintae_core.readiness import VERSIONS_LOCK_KEY
from pintae_rules.calendar import calendar_from_data
from pintae_rules.fixtures import run_suite, suite_hash
from pintae_rules.packs import PackError, content_hash, pack_from_data


def _d(v: str | None) -> date | None:
    return date.fromisoformat(v) if v else None


class PublicationRefused(Exception):
    def __init__(self, reason: str, detail: Any = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.detail = detail


def _lock(s: Session) -> None:
    """Exclusive versions lock: waits for in-flight approvals, blocks new ones (B1-009)."""
    s.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": VERSIONS_LOCK_KEY})


def _publisher(s: Session, vendor_user_id: uuid.UUID) -> VendorUser:
    v = s.get(VendorUser, vendor_user_id)
    if v is None or v.role != "publisher" or v.disabled_at is not None:
        raise PublicationRefused("not_a_publisher")
    return v


def _current_calendar_provisions(s: Session) -> list[Any]:
    row = s.execute(
        select(CalendarVersion)
        .where(CalendarVersion.status == "published")
        .order_by(CalendarVersion.published_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if row is None:
        return []
    from pintae_rules.calendar import Provision

    out = []
    for p in s.execute(
        select(ProvisionRow).where(ProvisionRow.calendar_version_id == row.id)
    ).scalars():
        out.append(
            Provision(
                p.code,
                p.kind,
                p.applies_from,
                p.applies_to,
                p.selector,
                p.effect,
                p.rule_code,
                tuple(p.source_refs.get("refs", [])),
            )
        )
    return out


def publish_rule_pack(
    engine: Engine,
    data: Mapping[str, Any],
    fixtures: Sequence[Mapping[str, Any]],
    vendor_user_id: uuid.UUID,
    confirmed_hash: bytes,
) -> uuid.UUID:
    try:
        pack = pack_from_data(data)
    except PackError as exc:
        raise PublicationRefused("invalid_pack", str(exc)) from exc
    digest = content_hash(data)
    with Session(engine) as s, s.begin():
        _lock(s)
        _publisher(s, vendor_user_id)
        existing = s.execute(
            select(RulePackRow).where(RulePackRow.code == pack.code)
        ).scalar_one_or_none()
        if existing is not None:
            if existing.content_hash != digest:
                raise PublicationRefused("content_changed_under_existing_code", pack.code)
            if existing.status == "withdrawn":
                raise PublicationRefused("version_withdrawn", pack.code)
            return existing.id  # idempotent on code and hash
        if not fixtures:
            raise PublicationRefused("no_fixture_suite")
        failures = run_suite(pack, fixtures, _current_calendar_provisions(s))
        if failures:
            raise PublicationRefused("fixture_suite_failed", [f.__dict__ for f in failures])
        if confirmed_hash != digest:
            raise PublicationRefused("confirmed_hash_differs_from_fixture_run")
        now = datetime.now(tz=UTC)
        row = RulePackRow(
            code=pack.code,
            basis=pack.basis,
            released_on=pack.released_on,
            effective_from=pack.effective_from,
            effective_label=pack.effective_label,
            status="published",
            content_hash=digest,
            published_at=now,
            content=dict(data),
        )
        s.add(row)
        s.flush()
        for r in pack.rules:
            s.add(
                RuleRow(
                    rule_pack_id=row.id,
                    code=r.code,
                    severity=r.severity,
                    applies_to=dict(r.applies_to),
                    valid_from=r.valid_from,
                    valid_to=r.valid_to,
                    source_refs={"refs": list(r.source_refs)},
                    description=r.description,
                )
            )
        s.add(
            Publication(
                object_type="rule_pack",
                object_id=row.id,
                content_hash=digest,
                fixture_run_ref=suite_hash(pack, fixtures).hex(),
                fixture_hash=digest,
                confirmed_by=vendor_user_id,
                confirmed_at=now,
            )
        )
        return row.id


def publish_calendar(
    engine: Engine, data: Mapping[str, Any], vendor_user_id: uuid.UUID, confirmed_hash: bytes
) -> uuid.UUID:
    cal = calendar_from_data(data)  # validates structure
    for rule in cal.rules.values():
        if not rule.source_refs:
            raise PublicationRefused("calendar_rule_without_source", rule.segment)
    digest = content_hash(data)
    with Session(engine) as s, s.begin():
        _lock(s)
        _publisher(s, vendor_user_id)
        existing = s.execute(
            select(CalendarVersion).where(CalendarVersion.code == cal.code)
        ).scalar_one_or_none()
        if existing is not None:
            if existing.content_hash != digest:
                raise PublicationRefused("content_changed_under_existing_code", cal.code)
            if existing.status == "withdrawn":
                raise PublicationRefused("version_withdrawn", cal.code)
            return existing.id
        if confirmed_hash != digest:
            raise PublicationRefused("confirmed_hash_differs")
        now = datetime.now(tz=UTC)
        row = CalendarVersion(
            code=cal.code,
            basis=cal.basis,
            source_refs={"refs": list(cal.source_refs)},
            effective_from=None,
            effective_label=data.get("effective_label", "assumed"),
            status="published",
            content_hash=digest,
            published_at=now,
            content=dict(data),
        )
        s.add(row)
        s.flush()
        for r in data["rules"]:
            s.add(
                CalendarRuleRow(
                    calendar_version_id=row.id,
                    segment=r["segment"],
                    deadline_basis=r["deadline_basis"],
                    appoint_by=_d(r.get("appoint_by")),
                    implement_by=_d(r.get("implement_by")),
                    candidate_segments=r.get("candidate_segments"),
                    source_refs={"refs": list(r.get("source_refs") or [])},
                    note=r.get("note"),
                    discrepancy=r.get("discrepancy"),
                )
            )
        for p in data.get("provisions", []):
            s.add(
                ProvisionRow(
                    calendar_version_id=row.id,
                    code=p["code"],
                    kind=p["kind"],
                    applies_from=_d(p.get("applies_from")),
                    applies_to=_d(p.get("applies_to")),
                    selector=p.get("selector") or {},
                    effect=p["effect"],
                    rule_code=p.get("rule_code"),
                    source_refs={"refs": list(p.get("source_refs") or [])},
                )
            )
        s.add(
            Publication(
                object_type="calendar_version",
                object_id=row.id,
                content_hash=digest,
                fixture_run_ref="calendar-structure-check",
                fixture_hash=digest,
                confirmed_by=vendor_user_id,
                confirmed_at=now,
            )
        )
        return row.id


def withdraw(engine: Engine, object_type: str, code: str, vendor_user_id: uuid.UUID) -> uuid.UUID:
    """Withdraw a published rule pack or calendar version: a status-only change (B1-012).

    Withdrawn is terminal: content stays frozen, runs pinned to the version stay pinned and
    keep loading it, and the code can never be published again. A correction is a new code.
    """
    tables = {"rule_pack": "rule_packs", "calendar_version": "calendar_versions"}
    if object_type not in tables:
        raise PublicationRefused("unknown_object_type", object_type)
    table = tables[object_type]
    with Session(engine) as s, s.begin():
        _lock(s)
        _publisher(s, vendor_user_id)
        row = s.execute(
            text(f"SELECT id, status FROM {table} WHERE code = :c FOR UPDATE"), {"c": code}
        ).one_or_none()
        if row is None:
            raise PublicationRefused("not_found", code)
        if row.status != "published":
            raise PublicationRefused("not_published", row.status)
        s.execute(text(f"UPDATE {table} SET status = 'withdrawn' WHERE id = :i"), {"i": row.id})
        pid: uuid.UUID = row.id
        return pid


def ensure_publisher(engine: Engine, email: str) -> uuid.UUID:
    """Local and test seeding only: a vendor publisher row without usable credentials."""
    with Session(engine) as s, s.begin():
        v = s.execute(select(VendorUser).where(VendorUser.email == email)).scalar_one_or_none()
        if v is None:
            v = VendorUser(
                email=email,
                role="publisher",
                password_hash="!disabled",  # noqa: S106 - unusable marker, not a secret
                totp_secret_enc=b"",
            )
            s.add(v)
            s.flush()
        return v.id
