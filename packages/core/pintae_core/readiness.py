"""Readiness services shared by the API and the worker (no web imports).

Every function takes a tenancy session. Status is always computed by
``pintae_rules.status``; this module only gathers its inputs (R-03).
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from sqlalchemy import func, or_, select, text, update
from sqlalchemy.orm import Session

from pintae_core.calendar_content import UNVERIFIED, calendar_rows_data, same_calendar
from pintae_core.models import (
    AspStatus,
    CalendarVersion,
    CheckRun,
    ClientEntity,
    ColumnMapping,
    FindingException,
    FindingRow,
    ReadinessSnapshot,
    Report,
    RulePackRow,
    RuleRow,
    SegmentAssessment,
    StagedRow,
    Upload,
    ValueMapping,
)
from pintae_ingest.mapper import apply_mapping
from pintae_ingest.parsers import ParsedRow
from pintae_rules import engine as rules_engine
from pintae_rules import status as st
from pintae_rules.calendar import Calendar, DeadlineView, calendar_from_data, deadline_view
from pintae_rules.dates import dubai_date
from pintae_rules.packs import PackRef, RulePack, content_hash, pack_from_data, select_current

DATASETS = ("customers", "items", "invoices")
PROFILE_FIELDS = {
    "vat_registered": "vat_registered",
    "trn": "trn",
    "tin": "tin",
    "registration_type": "registration_type",
    "licence_number": "licence_number",
    "licence_authority": "licence_authority",
    "passport_country": "passport_country",
    "address_line": "address_line",
    "city": "city",
    "country_code": "country_code",
    "emirate": "emirate_code",
}


class DomainError(Exception):
    """A request that cannot proceed. ``code`` maps to an HTTP status in the API."""

    def __init__(self, code: int, reason: str, detail: dict[str, Any] | None = None) -> None:
        super().__init__(reason)
        self.code = code
        self.reason = reason
        self.detail = detail or {}


# One advisory-lock key for "published reference versions". Publication takes it
# exclusively; approval takes it shared, so a pack or calendar cannot be published between
# an approval's pin comparison and its commit (B1-009, TRD 6.2).
VERSIONS_LOCK_KEY = 0x50494E5441450001  # "PINTAE" + 1


def lock_versions_shared(s: Session) -> None:
    s.execute(text("SELECT pg_advisory_xact_lock_shared(:k)"), {"k": VERSIONS_LOCK_KEY})


def lock_entity(s: Session, entity_id: uuid.UUID) -> ClientEntity:
    """Row lock on the entity. Every change to a version a result pins (segment, mapping,
    value table, profile, upload, run) and every approval takes it, so they serialise."""
    ent = s.execute(
        select(ClientEntity).where(ClientEntity.id == entity_id).with_for_update()
    ).scalar_one_or_none()
    if ent is None or ent.deleted_at is not None:
        raise DomainError(
            404, "not_found", {"object_type": "client_entity", "object_id": str(entity_id)}
        )
    return ent


def fingerprint_bytes(text_fp: str) -> bytes:
    return hashlib.sha256(text_fp.encode()).digest()


def canonical_hash(data: Any) -> bytes:
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":")).encode()).digest()


# ----------------------------------------------------------------------------- reference


def load_pack(row: RulePackRow) -> RulePack:
    """The one way to read a stored pack: recompute the hash of the frozen content (B1-012)."""
    if content_hash(row.content) != row.content_hash or row.content.get("code") != row.code:
        raise DomainError(500, "rule_pack_content_hash_mismatch", {"code": row.code})
    return pack_from_data(row.content)


def current_pack(s: Session, today: date) -> tuple[RulePackRow, RulePack]:
    rows = s.execute(select(RulePackRow).where(RulePackRow.status == "published")).scalars().all()
    refs = [
        PackRef(
            r.code,
            r.effective_from or r.released_on,
            int(r.published_at.timestamp() * 1e6) if r.published_at else 0,
        )
        for r in rows
    ]
    chosen = select_current(refs, today)
    if chosen is None:
        raise DomainError(503, "no_rule_pack_in_force")
    row = next(r for r in rows if r.code == chosen.code)
    return row, load_pack(row)


LEGACY = "legacy_unverified"


def current_calendar(s: Session) -> Calendar:
    """The newest published calendar whose content is verified. A ``legacy_unverified``
    version (B1-014) is never chosen, so no run newly pins it."""
    row = s.execute(
        select(CalendarVersion)
        .where(
            CalendarVersion.status == "published",
            or_(
                CalendarVersion.content_origin.is_(None),
                CalendarVersion.content_origin.not_in(UNVERIFIED),
            ),
        )
        .order_by(CalendarVersion.published_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if row is None:
        raise DomainError(503, "no_calendar_published")
    return _calendar(s, row)


def calendar_by_code(s: Session, code: str) -> Calendar:
    """The calendar version a run pinned (B1-001), published or later withdrawn."""
    row = s.execute(
        select(CalendarVersion).where(CalendarVersion.code == code)
    ).scalar_one_or_none()
    if row is None:
        raise DomainError(500, "pinned_calendar_missing")
    return _calendar(s, row)


def newest_calendar_unverified(s: Session) -> str | None:
    """The code of the newest published calendar when its content is unverified (B1-015):
    reads fall back to an older verified version, and /readyz says so by name."""
    row = s.execute(
        select(CalendarVersion.code, CalendarVersion.content_origin)
        .where(CalendarVersion.status == "published")
        .order_by(CalendarVersion.published_at.desc())
        .limit(1)
    ).first()
    return row.code if row is not None and row.content_origin in UNVERIFIED else None


def calendar_is_legacy(s: Session, code: str | None) -> bool:
    if code is None:
        return False
    origin = s.execute(
        select(CalendarVersion.content_origin).where(CalendarVersion.code == code)
    ).scalar_one_or_none()
    return origin in UNVERIFIED


def _calendar(s: Session, row: CalendarVersion) -> Calendar:
    if row.content_origin in UNVERIFIED:
        raise DomainError(409, "calendar_legacy_unverified", {"code": row.code})
    data = calendar_rows_data(s, row.id, row.code, row.basis, row.source_refs)
    # B1-012: the calendar is read from its hashed, frozen content; the child rows must agree.
    content = row.content
    if (
        content is None
        or content_hash(content) != row.content_hash
        or content.get("code") != row.code
    ):
        raise DomainError(500, "calendar_content_hash_mismatch", {"code": row.code})
    cal = calendar_from_data(content)
    if not same_calendar(cal, calendar_from_data(data)):
        raise DomainError(500, "calendar_rows_differ_from_content", {"code": row.code})
    return cal


# ----------------------------------------------------------------------------- entity facts


def get_entity(s: Session, entity_id: uuid.UUID) -> ClientEntity:
    ent = s.get(ClientEntity, entity_id)
    if ent is None or ent.deleted_at is not None:
        raise DomainError(404, "not_found")
    return ent


def seller_profile(ent: ClientEntity) -> dict[str, str | None]:
    out: dict[str, str | None] = {}
    for key, attr in PROFILE_FIELDS.items():
        v = getattr(ent, attr)
        out[key] = None if v in (None, "", "unknown") else str(v)
    return out


def seller_profile_present(ent: ClientEntity) -> bool:
    return any(v is not None for v in seller_profile(ent).values())


def approved_segment(s: Session, ent: ClientEntity) -> SegmentAssessment | None:
    if ent.current_segment_assessment_id is None:
        return None
    a = s.get(SegmentAssessment, ent.current_segment_assessment_id)
    return a if a is not None and a.state == "approved" else None


def latest_assessment(s: Session, entity_id: uuid.UUID) -> SegmentAssessment | None:
    return s.execute(
        select(SegmentAssessment)
        .where(SegmentAssessment.entity_id == entity_id)
        .order_by(SegmentAssessment.version.desc())
        .limit(1)
    ).scalar_one_or_none()


def latest_uploads(s: Session, entity_id: uuid.UUID) -> dict[str, Upload]:
    out: dict[str, Upload] = {}
    rows = s.execute(
        select(Upload)
        .where(Upload.entity_id == entity_id, Upload.state == "parsed")
        .order_by(Upload.created_at.desc())
    ).scalars()
    for u in rows:
        out.setdefault(u.dataset, u)
    return out


def latest_live_uploads(s: Session, entity_id: uuid.UUID) -> dict[str, Upload]:
    """Newest upload per dataset that is not rejected or removed, whatever its parse state.

    B1-005: staleness after a re-upload is derived from the upload row itself, so it does
    not wait for the parse job."""
    out: dict[str, Upload] = {}
    rows = s.execute(
        select(Upload)
        .where(Upload.entity_id == entity_id, Upload.state.in_(("received", "parsed")))
        .order_by(Upload.created_at.desc(), Upload.id)
    ).scalars()
    for u in rows:
        out.setdefault(u.dataset, u)
    return out


def usable_mapping(s: Session, upload_id: uuid.UUID) -> ColumnMapping | None:
    """Latest confirmed or approved version: nothing is checked before confirmation."""
    return s.execute(
        select(ColumnMapping)
        .where(
            ColumnMapping.upload_id == upload_id, ColumnMapping.state.in_(("confirmed", "approved"))
        )
        .order_by(ColumnMapping.version.desc())
        .limit(1)
    ).scalar_one_or_none()


def approved_value_maps(s: Session, entity_id: uuid.UUID) -> dict[tuple[str, str], str]:
    rows = s.execute(
        select(ValueMapping).where(
            ValueMapping.entity_id == entity_id,
            ValueMapping.state == "approved",
            ValueMapping.target_code.is_not(None),
        )
    ).scalars()
    return {(r.kind, r.source_value): str(r.target_code) for r in rows}


def value_map_digest(maps: dict[tuple[str, str], str]) -> str:
    return canonical_hash(sorted([[*k, v] for k, v in maps.items()])).hex()[:16]


@dataclass
class RunPlan:
    uploads: dict[str, Upload]
    mappings: dict[str, ColumnMapping]
    value_maps: dict[tuple[str, str], str]
    versions: st.Versions


def plan_inputs(s: Session, ent: ClientEntity, today: date) -> RunPlan:
    pack_row, _ = current_pack(s, today)
    uploads = latest_uploads(s, ent.id)
    mappings: dict[str, ColumnMapping] = {}
    for ds, u in uploads.items():
        m = usable_mapping(s, u.id)
        if m is not None:
            mappings[ds] = m
    used = {ds: uploads[ds] for ds in mappings}
    vmaps = approved_value_maps(s, ent.id)
    seg = approved_segment(s, ent) or latest_assessment(s, ent.id)
    mv: dict[str, Any] = {ds: f"{m.id}:{m.version}" for ds, m in sorted(mappings.items())}
    mv["values"] = value_map_digest(vmaps)
    versions = st.Versions(
        rule_pack=pack_row.code,
        segment_version=seg.version if seg else None,
        mapping_versions=mv,
        profile_version=ent.profile_version,
        calendar_version=current_calendar(s).code,
        uploads={ds: str(u.id) for ds, u in sorted(latest_live_uploads(s, ent.id).items())},
    )
    return RunPlan(used, mappings, vmaps, versions)


def entity_state(s: Session, ent: ClientEntity) -> st.EntityState:
    has_upload = (
        s.execute(
            select(func.count()).select_from(Upload).where(Upload.entity_id == ent.id)
        ).scalar_one()
        > 0
    )
    seg = approved_segment(s, ent)
    present = frozenset(
        ds for ds, u in latest_uploads(s, ent.id).items() if usable_mapping(s, u.id)
    )
    return st.EntityState(
        has_upload=has_upload,
        approved_segment=seg.segment if seg else None,
        datasets_present=present,
        seller_profile_present=seller_profile_present(ent),
    )


# ----------------------------------------------------------------------------- runs


def create_run(
    s: Session, ent: ClientEntity, actor_id: uuid.UUID | None, today: date
) -> tuple[CheckRun, bool]:
    """Create (or return the identical existing) run. Returns (run, created)."""
    plan = plan_inputs(s, ent, today)
    if not plan.mappings:
        raise DomainError(422, "no_confirmed_mapping")
    seg = approved_segment(s, ent) or latest_assessment(s, ent.id)
    if seg is None:
        raise DomainError(422, "segment_assessment_required")
    pack_row, _ = current_pack(s, today)
    inputs = {
        "rule_pack": pack_row.code,
        "segment_assessment_id": str(seg.id),
        "segment_version": seg.version,
        "profile_version": ent.profile_version,
        "uploads": {
            ds: {"upload_id": str(u.id), "sha256": u.sha256.hex()}
            for ds, u in sorted(plan.uploads.items())
        },
        "mapping_versions": dict(plan.versions.mapping_versions),
        # B1-001: the calendar's provisions decide scope (PRV-2), so it is a run input.
        "calendar_version": plan.versions.calendar_version,
    }
    input_hash = canonical_hash(inputs)
    existing = s.execute(
        select(CheckRun).where(CheckRun.entity_id == ent.id, CheckRun.input_hash == input_hash)
    ).scalar_one_or_none()
    if existing is not None and existing.state != "failed":
        return existing, False
    newest = max(dubai_date(u.created_at) for u in plan.uploads.values())
    if existing is not None:
        existing.state = "queued"
        return existing, True
    run = CheckRun(
        firm_id=ent.firm_id,
        created_by=actor_id,
        entity_id=ent.id,
        rule_pack_id=pack_row.id,
        segment_assessment_id=seg.id,
        profile_version=ent.profile_version,
        inputs=inputs,
        input_hash=input_hash,
        newest_data_on=newest,
        state="queued",
    )
    s.add(run)
    s.flush()
    return run, True


def _dataset_input(s: Session, upload: Upload, mapping: ColumnMapping) -> rules_engine.DatasetInput:
    staged = s.execute(
        select(StagedRow)
        .where(StagedRow.upload_id == upload.id)
        .order_by(StagedRow.sheet, StagedRow.row_number)
    ).scalars()
    m = mapping.mapping
    sheet = m.get("sheet")
    header_row = int(m["header_row"])
    rows = [
        ParsedRow(r.row_number, tuple(r.cells.get("c", [])))
        for r in staged
        if (r.sheet or None) == (sheet or None)
    ]
    header = next((r for r in rows if r.row_number == header_row), None)
    headers = header.cells if header else ()
    return apply_mapping(str(upload.id), sheet, header_row, headers, rows, m["fields"])


def execute_run(
    s: Session, run: CheckRun, provisions_calendar: Calendar | None = None
) -> st.Counts:
    """Evaluate a run and write findings and the snapshot in the caller's transaction."""
    ent = get_entity(s, run.entity_id)
    pack_row = s.get(RulePackRow, run.rule_pack_id)
    assert pack_row is not None
    pack = load_pack(pack_row)
    seg = s.get(SegmentAssessment, run.segment_assessment_id)
    datasets: dict[str, rules_engine.DatasetInput | None] = dict.fromkeys(DATASETS)
    mapping_versions = run.inputs["mapping_versions"]
    for ds, info in run.inputs["uploads"].items():
        upload = s.get(Upload, uuid.UUID(info["upload_id"]))
        mid, mver = mapping_versions[ds].split(":")
        mapping = s.get(ColumnMapping, uuid.UUID(mid))
        assert upload is not None and mapping is not None and mapping.version == int(mver)
        datasets[ds] = _dataset_input(s, upload, mapping)
    pinned_cal = run.inputs.get("calendar_version")
    calendar = provisions_calendar or (
        calendar_by_code(s, pinned_cal) if pinned_cal else current_calendar(s)
    )
    inp = rules_engine.EngineInput(
        seller=seller_profile(ent),
        datasets=datasets,
        value_maps=approved_value_maps(s, ent.id),
        segment=seg.segment if seg else None,
        provisions=calendar.provisions,
    )
    result = rules_engine.run(pack, inp)
    rule_ids = {
        r.code: r.id
        for r in s.execute(select(RuleRow).where(RuleRow.rule_pack_id == pack_row.id)).scalars()
    }
    s.query(FindingRow).filter(FindingRow.run_id == run.id).delete()
    for f in result.findings:
        s.add(
            FindingRow(
                firm_id=run.firm_id,
                run_id=run.id,
                entity_id=run.entity_id,
                rule_id=rule_ids[f.rule_code],
                dataset=f.dataset,
                record_key=f.record_key,
                upload_id=uuid.UUID(f.upload_id) if f.upload_id else None,
                sheet=f.sheet,
                row_number=f.row_number,
                column_name=f.column_name,
                value_found=f.value_found,
                outcome=f.outcome,
                not_checked_reason=f.not_checked_reason,
                message=f.message,
                fingerprint=fingerprint_bytes(f.fingerprint),
            )
        )
    in_scope: dict[str, int] = {}
    for rec in result.records:
        if rec.scope == "in_scope":
            in_scope[rec.dataset] = in_scope.get(rec.dataset, 0) + 1
    records: dict[str, int] = dict.fromkeys(DATASETS, 0)
    for rec in result.records:
        if rec.dataset in records:
            records[rec.dataset] += 1
    run.inputs = {
        **run.inputs,
        "in_scope_at_run": in_scope,
        "records_at_run": records,
        "earliest_invoice_on": (
            result.earliest_invoice_on.isoformat() if result.earliest_invoice_on else None
        ),
    }
    run.result_hash = bytes.fromhex(result.result_hash)
    run.state = "succeeded"
    run.finished_at = func.now()
    s.flush()
    s.execute(
        update(ReadinessSnapshot)
        .where(ReadinessSnapshot.entity_id == run.entity_id, ReadinessSnapshot.is_current.is_(True))
        .values(is_current=False)
    )
    snap = ReadinessSnapshot(
        firm_id=run.firm_id,
        run_id=run.id,
        entity_id=run.entity_id,
        base_status=st.Status.REVIEW_PENDING.value,
        score_by_dataset={},
        failed_blockers=0,
        unchecked_blockers=0,
        unresolved_manual_reviews=0,
        not_assessed_self_billed=0,
        accepted_exceptions=0,
        mappings_approved=False,
        is_current=True,
    )
    s.add(snap)
    s.flush()
    return refresh_snapshot(s, run.id)


def run_mappings_approved(s: Session, run: CheckRun) -> bool:
    for ref in run.inputs["mapping_versions"].values():
        if ":" not in str(ref):
            continue
        mid, _ = str(ref).split(":")
        m = s.get(ColumnMapping, uuid.UUID(mid))
        if m is None or m.state != "approved":
            return False
    return True


def accepted_exceptions(s: Session, entity_id: uuid.UUID, rule_pack_id: uuid.UUID) -> set[bytes]:
    """Exceptions lapse when the pack changes: only those under the run's pack count."""
    rows = s.execute(
        select(FindingException.fingerprint).where(
            FindingException.entity_id == entity_id,
            FindingException.state == "accepted",
            FindingException.rule_pack_id == rule_pack_id,
        )
    ).scalars()
    return set(rows)


def refresh_snapshot(
    s: Session, run_id: uuid.UUID, *, reviewer_approved: bool | None = None
) -> st.Counts:
    """Recompute the run's counts and base status with the one status function."""
    run = s.get(CheckRun, run_id)
    snap = s.execute(
        select(ReadinessSnapshot).where(ReadinessSnapshot.run_id == run_id)
    ).scalar_one()
    assert run is not None
    ent = get_entity(s, run.entity_id)
    pack_row = s.get(RulePackRow, run.rule_pack_id)
    assert pack_row is not None
    frozen = {r.code: r.severity for r in load_pack(pack_row).rules}
    # B1-012: severity comes from the hashed, frozen pack content, never the child row.
    sev = {
        r.id: frozen[r.code]
        for r in s.execute(
            select(RuleRow).where(RuleRow.rule_pack_id == run.rule_pack_id)
        ).scalars()
    }
    rows = s.execute(select(FindingRow).where(FindingRow.run_id == run_id)).scalars().all()
    stored = [
        st.StoredFinding(
            f.fingerprint.hex(),
            f.dataset,
            f.record_key,
            sev[f.rule_id],
            f.outcome,
            f.review_resolution,
        )
        for f in rows
    ]
    accepted = {fp.hex() for fp in accepted_exceptions(s, run.entity_id, run.rule_pack_id)}
    counts = st.summarise(
        stored,
        accepted,
        run.inputs.get("in_scope_at_run", {}),
        run.inputs.get("records_at_run", {}),
    )
    approved_maps = run_mappings_approved(s, run)
    was_approved = (
        snap.base_status == st.Status.DATA_READY.value
        if reviewer_approved is None
        else reviewer_approved
    )
    base = st.base_status(
        entity_state(s, ent),
        counts,
        mappings_approved=approved_maps,
        reviewer_approved=was_approved,
    )
    snap.base_status = base.value
    snap.score_by_dataset = dict(counts.score_by_dataset)
    snap.failed_blockers = counts.failed_blockers
    snap.unchecked_blockers = counts.unchecked_blockers
    snap.unresolved_manual_reviews = counts.unresolved_manual_reviews
    snap.not_assessed_self_billed = counts.not_assessed_self_billed
    snap.accepted_exceptions = counts.accepted_exceptions
    snap.empty_datasets = len(counts.empty_datasets)
    snap.mappings_approved = approved_maps
    s.flush()
    return counts


def current_snapshot(s: Session, entity_id: uuid.UUID) -> ReadinessSnapshot | None:
    return s.execute(
        select(ReadinessSnapshot).where(
            ReadinessSnapshot.entity_id == entity_id, ReadinessSnapshot.is_current.is_(True)
        )
    ).scalar_one_or_none()


def run_versions(s: Session, run: CheckRun) -> st.Versions:
    pack = s.get(RulePackRow, run.rule_pack_id)
    seg = s.get(SegmentAssessment, run.segment_assessment_id)
    return st.Versions(
        rule_pack=pack.code if pack else None,
        segment_version=run.inputs.get("segment_version", seg.version if seg else None),
        mapping_versions=run.inputs["mapping_versions"],
        profile_version=run.profile_version,
        calendar_version=run.inputs.get("calendar_version"),
        uploads={ds: info["upload_id"] for ds, info in sorted(run.inputs["uploads"].items())},
    )


# ----------------------------------------------------------------------------- reads


@dataclass(frozen=True)
class EntityStatusView:
    entity_id: uuid.UUID
    status: st.Status
    label: str
    stale_reasons: list[str]
    base_status: st.Status
    counts: dict[str, Any]
    deadline: DeadlineView
    asp_status: str
    pack_code: str | None
    run_id: uuid.UUID | None


def _earliest_invoice(s: Session, snap: ReadinessSnapshot | None) -> date | None:
    if snap is None:
        return None
    run = s.get(CheckRun, snap.run_id)
    raw = run.inputs.get("earliest_invoice_on") if run else None
    return date.fromisoformat(raw) if raw else None


def read_status(s: Session, ent: ClientEntity, today: date, calendar: Calendar) -> EntityStatusView:
    """Effective status derived on read (AD-11): no stored stale flag, no job involved."""
    state = entity_state(s, ent)
    snap = current_snapshot(s, ent.id)
    seg = approved_segment(s, ent)
    latest = latest_assessment(s, ent.id)
    band_source = seg or latest
    view = deadline_view(
        calendar,
        seg.segment if seg else None,
        today,
        first_invoice_state=(seg.first_invoice_state if seg else None),
        first_invoice_on=(seg.first_invoice_on if seg else None),
        revenue_band=band_source.revenue_band if band_source else None,
        earliest_invoice_on=_earliest_invoice(s, snap),
    )
    asp = (
        s.execute(
            select(AspStatus.status).where(
                AspStatus.entity_id == ent.id, AspStatus.is_current.is_(True)
            )
        ).scalar_one_or_none()
        or "not_appointed"
    )
    run: CheckRun | None = s.get(CheckRun, snap.run_id) if snap else None
    counts_dict: dict[str, Any] = {}
    pack_code = None
    if snap is None or run is None:
        base = st.base_status(state, None, mappings_approved=False, reviewer_approved=False)
        eff, reasons = base, list[str]()
    else:
        counts = st.Counts(
            snap.failed_blockers,
            snap.unchecked_blockers,
            snap.unresolved_manual_reviews,
            snap.not_assessed_self_billed,
            snap.accepted_exceptions,
            snap.score_by_dataset,
            tuple(
                ds
                for ds in st.REQUIRED_DATASETS
                if run.inputs.get("records_at_run", {}).get(ds, 1) == 0
            ),
        )
        base = st.base_status(
            state,
            counts,
            mappings_approved=snap.mappings_approved,
            reviewer_approved=snap.base_status == st.Status.DATA_READY.value,
        )
        pinned = run_versions(s, run)
        plan = plan_inputs(s, ent, today)
        current = st.Versions(
            rule_pack=plan.versions.rule_pack,
            segment_version=(seg.version if seg else (latest.version if latest else None)),
            mapping_versions=plan.versions.mapping_versions,
            profile_version=ent.profile_version,
            calendar_version=calendar.code,
            uploads=plan.versions.uploads,
        )
        eff, reasons = st.effective_status(base, pinned, current, run.newest_data_on, today)
        if calendar_is_legacy(s, pinned.calendar_version):
            # B1-014: a result pinned to a calendar whose content cannot be verified.
            reasons = ["calendar_legacy_unverified", *reasons]
            if base in st.STALE_REPLACES:
                eff = st.Status.STALE
        pack_code = pinned.rule_pack
        counts_dict = {
            "failed_blockers": counts.failed_blockers,
            "unchecked_blockers": counts.unchecked_blockers,
            "unresolved_manual_reviews": counts.unresolved_manual_reviews,
            "not_assessed_self_billed": counts.not_assessed_self_billed,
            "accepted_exceptions": counts.accepted_exceptions,
            "score_by_dataset": counts.score_by_dataset,
            "empty_datasets": list(counts.empty_datasets),
        }
    return EntityStatusView(
        entity_id=ent.id,
        status=eff,
        label=st.label(eff, pack_code),
        stale_reasons=reasons,
        base_status=base,
        counts=counts_dict,
        deadline=view,
        asp_status=asp,
        pack_code=pack_code,
        run_id=run.id if run else None,
    )


def report_pins(s: Session, run: CheckRun, calendar: Calendar) -> dict[str, Any]:
    v = run_versions(s, run)
    return {
        "run_id": str(run.id),
        "rule_pack": v.rule_pack,
        "segment_version": v.segment_version,
        "mapping_versions": dict(v.mapping_versions),
        "profile_version": v.profile_version,
        "calendar_version": calendar.code,
        "uploads": dict(v.uploads),
    }


def current_pins(s: Session, ent: ClientEntity, today: date, calendar: Calendar) -> dict[str, Any]:
    plan = plan_inputs(s, ent, today)
    seg = approved_segment(s, ent) or latest_assessment(s, ent.id)
    snap = current_snapshot(s, ent.id)
    return {
        "run_id": str(snap.run_id) if snap else None,
        "rule_pack": plan.versions.rule_pack,
        "segment_version": seg.version if seg else None,
        "mapping_versions": dict(plan.versions.mapping_versions),
        "profile_version": ent.profile_version,
        "calendar_version": calendar.code,
        "uploads": dict(plan.versions.uploads),
    }


def report_currency(s: Session, report: Report, today: date, calendar: Calendar) -> str:
    """Current or Superseded, derived on read from pins against current versions."""
    if report.state != "approved":
        return "draft"
    ent = get_entity(s, report.entity_id)
    return "current" if report.pins == current_pins(s, ent, today, calendar) else "superseded"


def now_dubai_date(now: datetime) -> date:
    return dubai_date(now)
