"""B1 routes: entities, segment, uploads, mappings, runs, findings, ASP status, reports,
dashboard and reference data. Every database access goes through ``tenancy.session``."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, date, datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, File, Form, Header, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from pintae_api.deps import DECIDERS, Actor, actor, engine, store, today
from pintae_core import audit, idempotency, jobs, readiness, tenancy
from pintae_core.config import get_settings
from pintae_core.models import (
    AspStatus,
    CheckRun,
    ClientEntity,
    ColumnMapping,
    FindingException,
    FindingRow,
    Job,
    ReadinessSnapshot,
    Report,
    RulePackRow,
    RuleRow,
    SegmentAssessment,
    StagedRow,
    SystemFlag,
    Upload,
    ValueMapping,
)
from pintae_core.readiness import DomainError
from pintae_core.storage import ObjectStore, upload_key
from pintae_ingest.mapper import ABSENT, TARGET_FIELDS, MappingError, validate_for_confirm
from pintae_ingest.parsers import Limits, RejectFile, check_upload
from pintae_rules import status as st
from pintae_rules.dashboard import SortableRow, overdue_without_asp, risk_sort
from pintae_rules.segment import SegmentFacts, classify

router = APIRouter()

ActorDep = Annotated[Actor, Depends(actor)]
EngineDep = Annotated[Engine, Depends(engine)]
StoreDep = Annotated[ObjectStore, Depends(store)]
TodayDep = Annotated[date, Depends(today)]


def not_found(object_type: str, object_id: Any) -> DomainError:
    return DomainError(404, "not_found", {"object_type": object_type, "object_id": str(object_id)})


def get_or_404(s: Session, model: type[Any], object_id: uuid.UUID, object_type: str) -> Any:
    obj = s.get(model, object_id)
    if obj is None or getattr(obj, "deleted_at", None) is not None:
        raise not_found(object_type, object_id)
    return obj


def entity_or_404(s: Session, entity_id: uuid.UUID) -> ClientEntity:
    ent: ClientEntity = get_or_404(s, ClientEntity, entity_id, "client_entity")
    return ent


def require_idempotency_key(key: str | None) -> str:
    if not key or len(key) > 200:
        raise DomainError(422, "idempotency_key_required")
    return key


# ----------------------------------------------------------------------------- reference


@router.get("/rule-packs")
def list_rule_packs(a: ActorDep, eng: EngineDep, day: TodayDep) -> dict[str, Any]:
    with tenancy.reference_session(eng) as s:
        rows = s.execute(select(RulePackRow).order_by(RulePackRow.released_on)).scalars().all()
        current = readiness.current_pack(s, day)[0].code
        return {
            "items": [
                {
                    "code": r.code,
                    "basis": r.basis,
                    "released_on": r.released_on.isoformat(),
                    "effective_from": r.effective_from.isoformat() if r.effective_from else None,
                    "effective_label": r.effective_label,
                    "status": r.status,
                    "current": r.code == current,
                    "source_refs": r.content.get("source_refs", []),
                }
                for r in rows
            ]
        }


@router.get("/calendar-versions")
def list_calendar(a: ActorDep, eng: EngineDep) -> dict[str, Any]:
    with tenancy.reference_session(eng) as s:
        cal = readiness.current_calendar(s)
        return {
            "current": cal.code,
            "basis": cal.basis,
            "rules": [
                {
                    "segment": r.segment,
                    "deadline_basis": r.deadline_basis,
                    "appoint_by": r.appoint_by.isoformat() if r.appoint_by else None,
                    "implement_by": r.implement_by.isoformat() if r.implement_by else None,
                    "source_refs": list(r.source_refs),
                    "discrepancy": r.discrepancy,
                }
                for r in cal.rules.values()
            ],
        }


# ----------------------------------------------------------------------------- entities


class EntityIn(BaseModel):
    legal_name: str = Field(min_length=1, max_length=300)
    source_ledger: str = Field(default="excel", max_length=50)


class ProfileIn(BaseModel):
    legal_name: str | None = Field(default=None, min_length=1, max_length=300)
    registration_type: Literal["TL", "EID", "PAS", "CD", "unknown"] | None = None
    licence_number: str | None = None
    licence_authority: str | None = None
    passport_country: str | None = None
    address_line: str | None = None
    city: str | None = None
    emirate_code: Literal["AUH", "DXB", "SHJ", "UAQ", "FUJ", "AJM", "RAK"] | None = None
    country_code: str | None = None
    vat_registered: Literal["yes", "no", "unknown"] | None = None
    trn: str | None = Field(default=None, pattern=r"^[0-9]{15}$")
    tin: str | None = Field(default=None, pattern=r"^[0-9]{10}$")


def deadline_json(v: Any) -> dict[str, Any]:
    return {
        "segment": v.segment,
        "segment_confirmed": v.segment_confirmed,
        "segment_label": v.segment if v.segment_confirmed else "Segment not confirmed",
        "calendar_version": v.calendar_code,
        "basis": v.basis,
        "appoint_by": v.governing_appoint_by.isoformat() if v.governing_appoint_by else None,
        "implement_by": v.governing_implement_by.isoformat() if v.governing_implement_by else None,
        "days_remaining": v.days_remaining,
        "display": v.display,
        "appoint_by_passed": v.appoint_by_passed,
        "outcomes": [
            {
                "segment": o.segment,
                "label": o.label,
                "appoint_by": o.appoint_by.isoformat() if o.appoint_by else None,
                "implement_by": o.implement_by.isoformat() if o.implement_by else None,
                "source_refs": list(o.source_refs),
            }
            for o in v.outcomes
        ],
        "notes": list(v.notes),
        "flags": list(v.flags),
    }


def status_json(view: readiness.EntityStatusView) -> dict[str, Any]:
    return {
        "status": view.status.value,
        "label": view.label,
        "stale_reasons": view.stale_reasons,
        "base_status": view.base_status.value,
        "counts": view.counts,
        "rule_pack": view.pack_code,
        "run_id": str(view.run_id) if view.run_id else None,
        "asp_status": view.asp_status,
        "deadline": deadline_json(view.deadline),
    }


def entity_json(ent: ClientEntity) -> dict[str, Any]:
    return {
        "id": str(ent.id),
        "legal_name": ent.legal_name,
        "profile_version": ent.profile_version,
        "profile": readiness.seller_profile(ent),
    }


@router.post("/entities", status_code=201)
def create_entity(body: EntityIn, a: ActorDep, eng: EngineDep) -> dict[str, Any]:
    with tenancy.session(a.firm_id, eng) as s:
        ent = ClientEntity(
            firm_id=a.firm_id,
            created_by=a.user_id,
            legal_name=body.legal_name,
            source_ledger=body.source_ledger,
        )
        s.add(ent)
        s.flush()
        s.add(
            AspStatus(firm_id=a.firm_id, entity_id=ent.id, status="not_appointed", is_current=True)
        )
        audit.record(
            s,
            firm_id=a.firm_id,
            action="entity.created",
            object_type="client_entity",
            object_id=ent.id,
            actor_id=a.user_id,
        )
        return entity_json(ent)


@router.get("/entities/{entity_id}")
def get_entity(entity_id: uuid.UUID, a: ActorDep, eng: EngineDep, day: TodayDep) -> dict[str, Any]:
    with tenancy.session(a.firm_id, eng) as s:
        ent = entity_or_404(s, entity_id)
        cal = readiness.current_calendar(s)
        return {**entity_json(ent), **status_json(readiness.read_status(s, ent, day, cal))}


@router.patch("/entities/{entity_id}")
def patch_entity(
    entity_id: uuid.UUID, body: ProfileIn, a: ActorDep, eng: EngineDep
) -> dict[str, Any]:
    with tenancy.session(a.firm_id, eng) as s:
        ent = readiness.lock_entity(s, entity_id)
        changes = body.model_dump(exclude_unset=True)
        for k, v in changes.items():
            setattr(ent, k, v)
        if changes:
            ent.profile_version += 1  # every profile change is a new version (staleness)
        audit.record(
            s,
            firm_id=a.firm_id,
            action="entity.profile_changed",
            object_type="client_entity",
            object_id=ent.id,
            actor_id=a.user_id,
            detail={"fields": sorted(changes), "profile_version": ent.profile_version},
        )
        return entity_json(ent)


@router.get("/dashboard")
def dashboard(a: ActorDep, eng: EngineDep, day: TodayDep) -> dict[str, Any]:
    """Multi-client view for the signed-in firm only (MH-09). Totals equal the rows."""
    with tenancy.session(a.firm_id, eng) as s:
        cal = readiness.current_calendar(s)
        ents = (
            s.execute(select(ClientEntity).where(ClientEntity.deleted_at.is_(None))).scalars().all()
        )
        views = {e.id: (e, readiness.read_status(s, e, day, cal)) for e in ents}
        rows = risk_sort(
            [
                SortableRow(str(e.id), e.legal_name, v.deadline, v.asp_status)
                for e, v in views.values()
            ]
        )
        out = []
        for r in rows:
            e, v = views[uuid.UUID(r.entity_id)]
            out.append(
                {
                    "entity_id": r.entity_id,
                    "legal_name": e.legal_name,
                    "overdue_without_asp": overdue_without_asp(r),
                    **status_json(v),
                }
            )
        tiles: dict[str, int] = {}
        for row in out:
            tiles[row["status"]] = tiles.get(row["status"], 0) + 1
        return {
            "as_of": day.isoformat(),
            "calendar_version": cal.code,
            "rows": out,
            "totals": {
                "entities": len(out),
                "by_status": tiles,
                "past_appoint_by_without_asp": sum(1 for r in out if r["overdue_without_asp"]),
            },
        }


# ----------------------------------------------------------------------------- segment


class SegmentIn(BaseModel):
    entity_type: Literal["person", "government_entity"]
    revenue_band: Literal["ge_50m", "eq_50m", "lt_50m", "unknown"] = "unknown"
    newly_established: bool = False
    first_invoice_state: Literal["issued", "not_yet", "unknown"] | None = None
    first_invoice_on: date | None = None
    b2c_only: bool = False
    period_end: date | None = None
    evidence_type: (
        Literal["financial_statements", "other_documentation", "client_statement"] | None
    ) = None
    note: str | None = Field(default=None, max_length=2000)


class DecisionIn(BaseModel):
    decision: Literal["approve", "return"]
    note: str | None = Field(default=None, max_length=2000)


def segment_json(a: SegmentAssessment) -> dict[str, Any]:
    return {
        "id": str(a.id),
        "version": a.version,
        "segment": a.segment,
        "state": a.state,
        "revenue_band": a.revenue_band,
        "entity_type": a.entity_type,
    }


@router.post("/entities/{entity_id}/segment-assessments", status_code=201)
def propose_segment(
    entity_id: uuid.UUID, body: SegmentIn, a: ActorDep, eng: EngineDep
) -> dict[str, Any]:
    with tenancy.session(a.firm_id, eng) as s:
        ent = readiness.lock_entity(s, entity_id)
        seg = classify(
            SegmentFacts(body.entity_type, body.revenue_band, body.newly_established, body.b2c_only)
        )
        version = (
            s.execute(
                select(func.max(SegmentAssessment.version)).where(
                    SegmentAssessment.entity_id == ent.id
                )
            ).scalar()
            or 0
        ) + 1
        row = SegmentAssessment(
            firm_id=a.firm_id,
            created_by=a.user_id,
            entity_id=ent.id,
            version=version,
            segment=seg.value,
            state="proposed",
            **body.model_dump(),
        )
        s.add(row)
        s.flush()
        audit.record(
            s,
            firm_id=a.firm_id,
            action="segment.proposed",
            object_type="segment_assessment",
            object_id=row.id,
            actor_id=a.user_id,
            detail={"version": version, "segment": seg.value},
        )
        return segment_json(row)


@router.post("/segment-assessments/{assessment_id}/decision")
def decide_segment(
    assessment_id: uuid.UUID, body: DecisionIn, a: ActorDep, eng: EngineDep
) -> dict[str, Any]:
    a.require(DECIDERS)
    with tenancy.session(a.firm_id, eng) as s:
        row: SegmentAssessment = get_or_404(
            s, SegmentAssessment, assessment_id, "segment_assessment"
        )
        readiness.lock_entity(s, row.entity_id)
        if row.state != "proposed":
            raise DomainError(409, "assessment_not_proposed")
        row.state = "approved" if body.decision == "approve" else "returned"
        row.decided_by, row.decided_at = a.user_id, datetime.now(tz=UTC)
        if body.decision == "approve":
            ent = entity_or_404(s, row.entity_id)
            ent.current_segment_assessment_id = row.id  # staleness and supersession follow on read
        audit.record(
            s,
            firm_id=a.firm_id,
            action=f"segment.{row.state}",
            object_type="segment_assessment",
            object_id=row.id,
            actor_id=a.user_id,
            detail={"version": row.version, "segment": row.segment},
        )
        return segment_json(row)


# ----------------------------------------------------------------------------- uploads


def upload_json(u: Upload) -> dict[str, Any]:
    return {
        "id": str(u.id),
        "entity_id": str(u.entity_id),
        "dataset": u.dataset,
        "state": u.state,
        "reject_reason": u.reject_reason,
        "row_count": u.row_count,
        "byte_size": u.byte_size,
    }


@router.post("/entities/{entity_id}/uploads", status_code=202)
async def create_upload(
    entity_id: uuid.UUID,
    a: ActorDep,
    eng: EngineDep,
    st_: StoreDep,
    dataset: Annotated[Literal["customers", "items", "invoices"], Form()],
    file: Annotated[UploadFile, File()],
    idempotency_key: Annotated[str | None, Header()] = None,
) -> JSONResponse:
    key = require_idempotency_key(idempotency_key)
    cfg = get_settings()
    data = await file.read(cfg.max_upload_bytes + 1)
    name = file.filename or "upload"
    try:
        check_upload(
            name,
            len(data),
            Limits(cfg.max_upload_bytes, cfg.max_xlsx_uncompressed_bytes, cfg.max_rows),
        )
    except RejectFile as rej:
        return JSONResponse(
            status_code=422, content={"reason": rej.reason_code, "message": rej.message}
        )
    digest = hashlib.sha256(data).digest()
    route = "POST /entities/{id}/uploads"
    rhash = idempotency.request_hash(str(entity_id), dataset, digest)
    with tenancy.session(a.firm_id, eng) as s:
        ent = readiness.lock_entity(s, entity_id)
        prior = idempotency.lookup(s, a.firm_id, route, key, rhash)
        if prior is not None:
            return JSONResponse(status_code=202, content=prior)
        existing = s.execute(
            select(Upload).where(
                Upload.entity_id == ent.id, Upload.dataset == dataset, Upload.sha256 == digest
            )
        ).scalar_one_or_none()
        if existing is not None:
            body = {**upload_json(existing), "duplicate": True, "job_id": None}
            idempotency.remember(s, a.firm_id, route, key, rhash, body)
            return JSONResponse(status_code=200, content=body)
        skey = upload_key(a.firm_id, ent.id, dataset)
        st_.put(skey, data)
        up = Upload(
            firm_id=a.firm_id,
            created_by=a.user_id,
            entity_id=ent.id,
            dataset=dataset,
            sha256=digest,
            storage_key=skey,
            original_name=name[:255],
            byte_size=len(data),
            state="received",
        )
        s.add(up)
        s.flush()
        job = jobs.enqueue(
            s, firm_id=a.firm_id, kind="parse_upload", payload={"upload_id": str(up.id)}
        )
        audit.record(
            s,
            firm_id=a.firm_id,
            action="upload.received",
            object_type="upload",
            object_id=up.id,
            actor_id=a.user_id,
            detail={"dataset": dataset, "bytes": len(data)},
        )
        body = {**upload_json(up), "duplicate": False, "job_id": str(job.id)}
        idempotency.remember(s, a.firm_id, route, key, rhash, body)
        return JSONResponse(status_code=202, content=body)


@router.get("/uploads/{upload_id}")
def get_upload(upload_id: uuid.UUID, a: ActorDep, eng: EngineDep) -> dict[str, Any]:
    with tenancy.session(a.firm_id, eng) as s:
        return upload_json(get_or_404(s, Upload, upload_id, "upload"))


@router.get("/entities/{entity_id}/uploads")
def list_uploads(entity_id: uuid.UUID, a: ActorDep, eng: EngineDep) -> dict[str, Any]:
    with tenancy.session(a.firm_id, eng) as s:
        ent = entity_or_404(s, entity_id)
        rows = s.execute(
            select(Upload).where(Upload.entity_id == ent.id).order_by(Upload.created_at)
        ).scalars()
        return {"items": [upload_json(u) for u in rows]}


# ----------------------------------------------------------------------------- mappings


class MappingIn(BaseModel):
    sheet: str | None = None
    header_row: int = Field(ge=1)
    fields: dict[str, str | None]


def latest_mapping(s: Session, upload_id: uuid.UUID) -> ColumnMapping:
    m = s.execute(
        select(ColumnMapping)
        .where(ColumnMapping.upload_id == upload_id)
        .order_by(ColumnMapping.version.desc())
        .limit(1)
    ).scalar_one_or_none()
    if m is None:
        raise DomainError(409, "upload_not_parsed")
    return m


def headers_for(
    s: Session, upload_id: uuid.UUID, sheet: str | None, header_row: int
) -> tuple[str | None, ...]:
    row = (
        s.execute(
            select(StagedRow).where(
                StagedRow.upload_id == upload_id, StagedRow.row_number == header_row
            )
        )
        .scalars()
        .all()
    )
    for r in row:
        if (r.sheet or None) == (sheet or None):
            return tuple(r.cells.get("c", []))
    raise DomainError(422, "header_row_not_found")


def samples(
    s: Session, upload_id: uuid.UUID, m: dict[str, Any], headers: tuple[str | None, ...]
) -> dict[str, list[Any]]:
    """Five sample values per mapped field, for the Reviewer (MH-05). Response only, never logged."""
    idx = {h: i for i, h in enumerate(headers) if h}
    rows = (
        s.execute(
            select(StagedRow)
            .where(StagedRow.upload_id == upload_id, StagedRow.row_number > int(m["header_row"]))
            .order_by(StagedRow.row_number)
            .limit(5)
        )
        .scalars()
        .all()
    )
    out: dict[str, list[Any]] = {}
    for f, src in m["fields"].items():
        if src and src != ABSENT and src in idx:
            out[f] = [(r.cells.get("c", []) + [None] * 999)[idx[src]] for r in rows]
    return out


def data_rows(s: Session, upload_id: uuid.UUID, sheet: str | None, header_row: int) -> int:
    rows = s.execute(
        select(StagedRow.sheet).where(
            StagedRow.upload_id == upload_id, StagedRow.row_number > header_row
        )
    ).scalars()
    return sum(1 for sh in rows if (sh or None) == (sheet or None))


def mapping_json(s: Session, m: ColumnMapping, with_samples: bool = True) -> dict[str, Any]:
    up = s.get(Upload, m.upload_id)
    headers = headers_for(s, m.upload_id, m.mapping.get("sheet"), int(m.mapping["header_row"]))
    body: dict[str, Any] = {
        "id": str(m.id),
        "upload_id": str(m.upload_id),
        "dataset": up.dataset if up else None,
        "version": m.version,
        "state": m.state,
        "mapping": m.mapping,
        "headers": list(headers),
        "unmapped_fields": [f for f, v in m.mapping["fields"].items() if v is None],
        "absent_fields": [f for f, v in m.mapping["fields"].items() if v == ABSENT],
        # B1-002: a file with no rows below the header row can never count as checked.
        "data_rows": data_rows(
            s, m.upload_id, m.mapping.get("sheet"), int(m.mapping["header_row"])
        ),
    }
    if with_samples:
        body["samples"] = samples(s, m.upload_id, m.mapping, headers)
    return body


@router.get("/uploads/{upload_id}/mapping")
def get_mapping(upload_id: uuid.UUID, a: ActorDep, eng: EngineDep) -> dict[str, Any]:
    with tenancy.session(a.firm_id, eng) as s:
        get_or_404(s, Upload, upload_id, "upload")
        return mapping_json(s, latest_mapping(s, upload_id))


@router.put("/uploads/{upload_id}/mapping")
def put_mapping(
    upload_id: uuid.UUID, body: MappingIn, a: ActorDep, eng: EngineDep
) -> dict[str, Any]:
    with tenancy.session(a.firm_id, eng) as s:
        up: Upload = get_or_404(s, Upload, upload_id, "upload")
        readiness.lock_entity(s, up.entity_id)
        unknown = [f for f in body.fields if f not in TARGET_FIELDS[up.dataset]]
        if unknown:
            raise DomainError(422, "unknown_target_fields", {"fields": unknown})
        headers = headers_for(s, upload_id, body.sheet, body.header_row)
        m = latest_mapping(s, upload_id)
        content = {
            "sheet": body.sheet,
            "header_row": body.header_row,
            "fields": {f: body.fields.get(f) for f in TARGET_FIELDS[up.dataset]},
        }
        from pintae_ingest.mapper import header_fingerprint

        if m.state == "draft":
            m.mapping, m.header_fingerprint = content, header_fingerprint(headers)
        else:
            m = ColumnMapping(
                firm_id=a.firm_id,
                upload_id=upload_id,
                version=m.version + 1,
                header_fingerprint=header_fingerprint(headers),
                mapping=content,
                state="draft",
            )
            s.add(m)
        s.flush()
        return mapping_json(s, m)


@router.post("/uploads/{upload_id}/mapping/confirm")
def confirm_mapping(upload_id: uuid.UUID, a: ActorDep, eng: EngineDep) -> dict[str, Any]:
    with tenancy.session(a.firm_id, eng) as s:
        up: Upload = get_or_404(s, Upload, upload_id, "upload")
        readiness.lock_entity(s, up.entity_id)
        m = latest_mapping(s, upload_id)
        if m.state != "draft":
            raise DomainError(409, "mapping_not_draft")
        headers = headers_for(s, upload_id, m.mapping.get("sheet"), int(m.mapping["header_row"]))
        try:
            validate_for_confirm(up.dataset, m.mapping["fields"], headers)
        except MappingError as exc:
            raise DomainError(422, "mapping_incomplete", {"message": str(exc)}) from exc
        m.state, m.confirmed_by, m.confirmed_at = "confirmed", a.user_id, datetime.now(tz=UTC)
        audit.record(
            s,
            firm_id=a.firm_id,
            action="mapping.confirmed",
            object_type="column_mapping",
            object_id=m.id,
            actor_id=a.user_id,
            detail={
                "version": m.version,
                "absent": sorted(f for f, v in m.mapping["fields"].items() if v == ABSENT),
            },
        )
        return mapping_json(s, m)


def refresh_current(s: Session, entity_id: uuid.UUID) -> None:
    snap = readiness.current_snapshot(s, entity_id)
    if snap is not None:
        readiness.refresh_snapshot(s, snap.run_id)


@router.post("/mappings/{mapping_id}/decision")
def decide_mapping(
    mapping_id: uuid.UUID, body: DecisionIn, a: ActorDep, eng: EngineDep
) -> dict[str, Any]:
    a.require(DECIDERS)
    with tenancy.session(a.firm_id, eng) as s:
        m: ColumnMapping = get_or_404(s, ColumnMapping, mapping_id, "column_mapping")
        locked_up = s.get(Upload, m.upload_id)
        assert locked_up is not None
        readiness.lock_entity(s, locked_up.entity_id)
        if m.state != "confirmed":
            raise DomainError(409, "mapping_not_confirmed")
        if body.decision == "approve":
            m.state, m.approved_by, m.approved_at = "approved", a.user_id, datetime.now(tz=UTC)
        else:
            m.state = "returned"
        s.flush()
        up = s.get(Upload, m.upload_id)
        assert up is not None
        refresh_current(s, up.entity_id)
        audit.record(
            s,
            firm_id=a.firm_id,
            action=f"mapping.{m.state}",
            object_type="column_mapping",
            object_id=m.id,
            actor_id=a.user_id,
            detail={"version": m.version},
        )
        return mapping_json(s, m, with_samples=False)


class ValueMapIn(BaseModel):
    kind: Literal["unit", "emirate", "tax_treatment", "document_type", "buyer_class", "country"]
    source_value: str = Field(min_length=1, max_length=200)
    target_code: str | None = Field(default=None, max_length=20)


class ValueMapsIn(BaseModel):
    items: list[ValueMapIn]


class ValueDecisionIn(BaseModel):
    items: list[ValueMapIn]
    decision: Literal["approve"]


@router.get("/entities/{entity_id}/value-mappings")
def get_value_maps(entity_id: uuid.UUID, a: ActorDep, eng: EngineDep) -> dict[str, Any]:
    with tenancy.session(a.firm_id, eng) as s:
        ent = entity_or_404(s, entity_id)
        rows = s.execute(select(ValueMapping).where(ValueMapping.entity_id == ent.id)).scalars()
        return {
            "items": [
                {
                    "kind": r.kind,
                    "source_value": r.source_value,
                    "target_code": r.target_code,
                    "state": r.state,
                }
                for r in rows
            ]
        }


@router.put("/entities/{entity_id}/value-mappings")
def put_value_maps(
    entity_id: uuid.UUID, body: ValueMapsIn, a: ActorDep, eng: EngineDep
) -> dict[str, Any]:
    with tenancy.session(a.firm_id, eng) as s:
        ent = readiness.lock_entity(s, entity_id)
        for it in body.items:
            row = s.execute(
                select(ValueMapping).where(
                    ValueMapping.entity_id == ent.id,
                    ValueMapping.kind == it.kind,
                    ValueMapping.source_value == it.source_value,
                )
            ).scalar_one_or_none()
            if row is None:
                row = ValueMapping(
                    firm_id=a.firm_id, entity_id=ent.id, kind=it.kind, source_value=it.source_value
                )
                s.add(row)
            row.target_code, row.state, row.approved_by = it.target_code, "confirmed", None
        s.flush()
    return get_value_maps(entity_id, a, eng)


@router.post("/entities/{entity_id}/value-mappings/decision")
def decide_value_maps(
    entity_id: uuid.UUID, body: ValueDecisionIn, a: ActorDep, eng: EngineDep
) -> dict[str, Any]:
    a.require(DECIDERS)
    with tenancy.session(a.firm_id, eng) as s:
        ent = readiness.lock_entity(s, entity_id)
        for it in body.items:
            row = s.execute(
                select(ValueMapping).where(
                    ValueMapping.entity_id == ent.id,
                    ValueMapping.kind == it.kind,
                    ValueMapping.source_value == it.source_value,
                )
            ).scalar_one_or_none()
            if row is None:
                raise not_found("value_mapping", None)
            row.state, row.approved_by = "approved", a.user_id
        audit.record(
            s,
            firm_id=a.firm_id,
            action="value_mappings.approved",
            object_type="client_entity",
            object_id=ent.id,
            actor_id=a.user_id,
            detail={"count": len(body.items)},
        )
    return get_value_maps(entity_id, a, eng)


# ----------------------------------------------------------------------------- runs


def run_json(s: Session, run: CheckRun) -> dict[str, Any]:
    snap = s.execute(
        select(ReadinessSnapshot).where(ReadinessSnapshot.run_id == run.id)
    ).scalar_one_or_none()
    pack = s.get(RulePackRow, run.rule_pack_id)
    return {
        "id": str(run.id),
        "entity_id": str(run.entity_id),
        "state": run.state,
        "rule_pack": pack.code if pack else None,
        "newest_data_on": run.newest_data_on.isoformat(),
        "result_hash": run.result_hash.hex() if run.result_hash else None,
        "base_status": snap.base_status if snap else None,
    }


@router.post("/entities/{entity_id}/runs", status_code=202)
def start_run(
    entity_id: uuid.UUID,
    a: ActorDep,
    eng: EngineDep,
    day: TodayDep,
    idempotency_key: Annotated[str | None, Header()] = None,
) -> JSONResponse:
    key = require_idempotency_key(idempotency_key)
    route = "POST /entities/{id}/runs"
    rhash = idempotency.request_hash(str(entity_id))
    with tenancy.session(a.firm_id, eng) as s:
        ent = readiness.lock_entity(s, entity_id)
        prior = idempotency.lookup(s, a.firm_id, route, key, rhash)
        if prior is not None:
            return JSONResponse(status_code=202, content=prior)
        run, created = readiness.create_run(s, ent, a.user_id, day)
        job_id = None
        if created:
            job = jobs.enqueue(
                s, firm_id=a.firm_id, kind="run_checks", payload={"run_id": str(run.id)}
            )
            job_id = str(job.id)
            audit.record(
                s,
                firm_id=a.firm_id,
                action="run.started",
                object_type="check_run",
                object_id=run.id,
                actor_id=a.user_id,
                detail={"rule_pack": run.inputs["rule_pack"]},
            )
        body = {**run_json(s, run), "job_id": job_id, "reused": not created}
        idempotency.remember(s, a.firm_id, route, key, rhash, body)
        return JSONResponse(status_code=202, content=body)


@router.get("/runs/{run_id}")
def get_run(run_id: uuid.UUID, a: ActorDep, eng: EngineDep) -> dict[str, Any]:
    with tenancy.session(a.firm_id, eng) as s:
        return run_json(s, get_or_404(s, CheckRun, run_id, "check_run"))


@router.get("/jobs/{job_id}")
def get_job(job_id: uuid.UUID, a: ActorDep, eng: EngineDep) -> dict[str, Any]:
    with tenancy.session(a.firm_id, eng) as s:
        j: Job = get_or_404(s, Job, job_id, "job")
        return {
            "id": str(j.id),
            "kind": j.kind,
            "state": j.state,
            "attempts": j.attempts,
            "last_error_code": j.last_error_code,
        }


# ----------------------------------------------------------------------------- findings


@router.get("/entities/{entity_id}/findings")
def list_findings(entity_id: uuid.UUID, a: ActorDep, eng: EngineDep) -> dict[str, Any]:
    with tenancy.session(a.firm_id, eng) as s:
        ent = entity_or_404(s, entity_id)
        snap = readiness.current_snapshot(s, ent.id)
        if snap is None:
            return {"run_id": None, "items": []}
        rows = s.execute(
            select(FindingRow, RuleRow)
            .join(RuleRow, RuleRow.id == FindingRow.rule_id)
            .where(FindingRow.run_id == snap.run_id)
            .order_by(FindingRow.dataset, RuleRow.code, FindingRow.row_number)
            .limit(500)
        ).all()
        return {
            "run_id": str(snap.run_id),
            "items": [
                {
                    "id": str(f.id),
                    "rule": r.code,
                    "severity": r.severity,
                    "source_refs": r.source_refs.get("refs", []),
                    "dataset": f.dataset,
                    "record_key": f.record_key,
                    "sheet": f.sheet,
                    "row": f.row_number,
                    "column": f.column_name,
                    "value_found": f.value_found,
                    "outcome": f.outcome,
                    "not_checked_reason": f.not_checked_reason,
                    "message": f.message,
                    "review_resolution": f.review_resolution,
                    "fingerprint": f.fingerprint.hex(),
                }
                for f, r in rows
            ],
        }


class ExceptionIn(BaseModel):
    reason: str = Field(min_length=3, max_length=2000)


class ExceptionDecisionIn(BaseModel):
    decision: Literal["accept", "reject"]


@router.post("/findings/{finding_id}/exceptions", status_code=201)
def propose_exception(
    finding_id: uuid.UUID, body: ExceptionIn, a: ActorDep, eng: EngineDep
) -> dict[str, Any]:
    with tenancy.session(a.firm_id, eng) as s:
        f: FindingRow = get_or_404(s, FindingRow, finding_id, "finding")
        if f.outcome != "fail":
            raise DomainError(409, "only_failed_findings_can_be_excepted")
        run = s.get(CheckRun, f.run_id)
        assert run is not None
        ex = FindingException(
            firm_id=a.firm_id,
            created_by=a.user_id,
            entity_id=f.entity_id,
            fingerprint=f.fingerprint,
            reason=body.reason,
            state="proposed",
            rule_pack_id=run.rule_pack_id,
        )
        s.add(ex)
        s.flush()
        audit.record(
            s,
            firm_id=a.firm_id,
            action="exception.proposed",
            object_type="finding_exception",
            object_id=ex.id,
            actor_id=a.user_id,
        )
        return {"id": str(ex.id), "state": ex.state}


@router.post("/exceptions/{exception_id}/decision")
def decide_exception(
    exception_id: uuid.UUID, body: ExceptionDecisionIn, a: ActorDep, eng: EngineDep
) -> dict[str, Any]:
    a.require(DECIDERS)
    with tenancy.session(a.firm_id, eng) as s:
        ex: FindingException = get_or_404(s, FindingException, exception_id, "finding_exception")
        readiness.lock_entity(s, ex.entity_id)
        if ex.state != "proposed":
            raise DomainError(409, "exception_not_proposed")
        ex.state = "accepted" if body.decision == "accept" else "rejected"
        ex.decided_by, ex.decided_at = a.user_id, datetime.now(tz=UTC)
        s.flush()
        refresh_current(s, ex.entity_id)
        audit.record(
            s,
            firm_id=a.firm_id,
            action=f"exception.{ex.state}",
            object_type="finding_exception",
            object_id=ex.id,
            actor_id=a.user_id,
        )
        return {"id": str(ex.id), "state": ex.state}


class ResolutionIn(BaseModel):
    finding_ids: list[uuid.UUID] = Field(min_length=1, max_length=500)
    resolution: Literal["confirmed_self_billed", "type_corrected"]


@router.post("/findings/review-resolutions")
def resolve_manual_review(body: ResolutionIn, a: ActorDep, eng: EngineDep) -> dict[str, Any]:
    a.require(DECIDERS)
    with tenancy.session(a.firm_id, eng) as s:
        entities: set[uuid.UUID] = set()
        for fid in body.finding_ids:
            f: FindingRow = get_or_404(s, FindingRow, fid, "finding")
            readiness.lock_entity(s, f.entity_id)
            if f.outcome != "manual_review":
                raise DomainError(409, "not_a_manual_review_finding", {"finding_id": str(fid)})
            f.review_resolution, f.resolved_by, f.resolved_at = (
                body.resolution,
                a.user_id,
                datetime.now(tz=UTC),
            )
            entities.add(f.entity_id)
        s.flush()
        for e in entities:
            refresh_current(s, e)
        audit.record(
            s,
            firm_id=a.firm_id,
            action="manual_review.resolved",
            object_type="finding",
            object_id=None,
            actor_id=a.user_id,
            detail={"count": len(body.finding_ids), "resolution": body.resolution},
        )
        return {"resolved": len(body.finding_ids)}


# ----------------------------------------------------------------------------- ASP status


class AspIn(BaseModel):
    status: Literal["not_appointed", "appointed", "onboarded", "live"]
    asp_name: str | None = Field(default=None, max_length=200)
    appointed_on: date | None = None
    emaratax_done: bool = False
    note: str | None = Field(default=None, max_length=2000)


@router.put("/entities/{entity_id}/asp-status")
def put_asp(entity_id: uuid.UUID, body: AspIn, a: ActorDep, eng: EngineDep) -> dict[str, Any]:
    a.require(DECIDERS)
    with tenancy.session(a.firm_id, eng) as s:
        ent = entity_or_404(s, entity_id)
        cur = s.execute(
            select(AspStatus).where(AspStatus.entity_id == ent.id, AspStatus.is_current.is_(True))
        ).scalar_one_or_none()
        if cur is not None:
            cur.is_current = False
            s.flush()
        row = AspStatus(firm_id=a.firm_id, entity_id=ent.id, is_current=True, **body.model_dump())
        s.add(row)
        audit.record(
            s,
            firm_id=a.firm_id,
            action="asp_status.changed",
            object_type="client_entity",
            object_id=ent.id,
            actor_id=a.user_id,
            detail={"status": body.status},
        )
        return {"entity_id": str(ent.id), "status": row.status}


# ----------------------------------------------------------------------------- reports


DISCLAIMER = (
    "Not an Accredited Service Provider; not an ASP validation result. "
    "Valid only while your accountant's record for this code shows Current."
)


def report_json(s: Session, r: Report, day: date) -> dict[str, Any]:
    cal = readiness.current_calendar(s)
    return {
        "id": str(r.id),
        "entity_id": str(r.entity_id),
        "reference_code": r.reference_code,
        "state": r.state,
        "watermark": "DRAFT" if r.state == "draft" else None,
        "pins": r.pins,
        "printed_status": r.printed_status,
        "currency": readiness.report_currency(s, r, day, cal),
        "disclaimer": DISCLAIMER,
    }


@router.post("/entities/{entity_id}/reports", status_code=201)
def draft_report(
    entity_id: uuid.UUID, a: ActorDep, eng: EngineDep, day: TodayDep
) -> dict[str, Any]:
    with tenancy.session(a.firm_id, eng) as s:
        ent = entity_or_404(s, entity_id)
        snap = readiness.current_snapshot(s, ent.id)
        if snap is None:
            raise DomainError(409, "no_run_to_report")
        run = s.get(CheckRun, snap.run_id)
        assert run is not None
        cal = readiness.current_calendar(s)
        code = "PAE-" + secrets.token_hex(4).upper()
        r = Report(
            firm_id=a.firm_id,
            created_by=a.user_id,
            entity_id=ent.id,
            run_id=run.id,
            reference_code=code,
            state="draft",
            pins=readiness.report_pins(s, run, cal),
        )
        s.add(r)
        s.flush()
        return report_json(s, r, day)


@router.get("/reports/lookup")
def lookup_report(code: str, a: ActorDep, eng: EngineDep, day: TodayDep) -> dict[str, Any]:
    with tenancy.session(a.firm_id, eng) as s:
        r = s.execute(select(Report).where(Report.reference_code == code)).scalar_one_or_none()
        if r is None:
            raise not_found("report", None)
        return report_json(s, r, day)


@router.get("/reports/{report_id}")
def get_report(report_id: uuid.UUID, a: ActorDep, eng: EngineDep, day: TodayDep) -> dict[str, Any]:
    with tenancy.session(a.firm_id, eng) as s:
        return report_json(s, get_or_404(s, Report, report_id, "report"), day)


class ApproveIn(BaseModel):
    pins: dict[str, Any]


@router.post("/reports/{report_id}/approve")
def approve_report(
    report_id: uuid.UUID,
    body: ApproveIn,
    request: Request,
    a: ActorDep,
    eng: EngineDep,
    day: TodayDep,
) -> dict[str, Any]:
    """Approval re-checks every pin against the current versions (AD-04, IT-07)."""
    a.require(DECIDERS)
    with tenancy.session(a.firm_id, eng) as s:
        frozen = s.get(SystemFlag, "approvals_frozen")
        if frozen is not None and frozen.value:
            raise DomainError(
                503, "approvals_frozen", {"message": frozen.reason or "Approvals are paused"}
            )
        # B1-009: shared versions lock (publication takes it exclusively), then the entity
        # row lock that every pinned-version change takes; pins are compared after both.
        readiness.lock_versions_shared(s)
        r: Report = get_or_404(s, Report, report_id, "report")
        ent = readiness.lock_entity(s, r.entity_id)
        s.refresh(r, with_for_update=True)
        if r.state != "draft":
            raise DomainError(409, "report_not_draft")
        cal = readiness.current_calendar(s)
        current = readiness.current_pins(s, ent, day, cal)
        if body.pins != r.pins or r.pins != current:
            raise DomainError(
                409, "stale", {"message": "Re-run required", "current_versions": current}
            )
        view = readiness.read_status(s, ent, day, cal)
        if view.status is st.Status.STALE:
            raise DomainError(
                409, "stale", {"stale_reasons": view.stale_reasons, "current_versions": current}
            )
        snap = readiness.current_snapshot(s, ent.id)
        assert snap is not None
        if not snap.mappings_approved:
            raise DomainError(409, "mappings_not_approved")
        printed: st.Status = view.status
        if view.status is st.Status.REVIEW_PENDING:
            readiness.refresh_snapshot(s, snap.run_id, reviewer_approved=True)
            printed = st.Status(snap.base_status)
        r.state, r.approved_by, r.approved_at = "approved", a.user_id, datetime.now(tz=UTC)
        r.printed_status = st.label(printed, r.pins.get("rule_pack"))
        r.content_hash = readiness.canonical_hash(
            {"pins": r.pins, "status": r.printed_status, "code": r.reference_code}
        )
        audit.record(
            s,
            firm_id=a.firm_id,
            action="report.approved",
            object_type="report",
            object_id=r.id,
            actor_id=a.user_id,
            detail={"pins": r.pins, "printed_status": printed.value},
        )
        s.flush()
        return report_json(s, r, day)
