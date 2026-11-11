"""Job handlers. Each runs inside the job firm's tenancy session and writes its result only
while its attempt is current (R-01)."""

from __future__ import annotations

import hashlib
import logging
import uuid
from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from pintae_core import jobs, readiness
from pintae_core.logging import log_event
from pintae_core.models import CheckRun, ColumnMapping, StagedRow, Upload
from pintae_core.storage import ObjectStore
from pintae_ingest.mapper import suggest
from pintae_ingest.parsers import Limits, RejectFile, parse

log = logging.getLogger("pintae.worker")


def parse_upload(s: Session, c: jobs.Claimed, store: ObjectStore, limits: Limits) -> None:
    upload = s.get(Upload, uuid.UUID(c.payload["upload_id"]))
    if upload is None:
        raise readiness.DomainError(404, "upload_missing")
    if upload.state != "received":
        return  # already terminal: a duplicate delivery changes nothing
    readiness.lock_entity(s, upload.entity_id)
    data = store.get(upload.storage_key)
    if hashlib.sha256(data).digest() != upload.sha256:
        raise readiness.DomainError(500, "stored_object_hash_mismatch")
    try:
        parsed = parse(data, upload.original_name, limits)
    except RejectFile as rej:
        upload.state = "rejected"
        upload.reject_reason = rej.reason_code
        log_event(log, "upload.rejected", upload_id=upload.id, reason_code=rej.reason_code)
        return
    for sheet in parsed.sheets:
        for r in sheet.rows:
            s.add(
                StagedRow(
                    firm_id=upload.firm_id,
                    upload_id=upload.id,
                    sheet=sheet.name,
                    row_number=r.row_number,
                    cells={"c": list(r.cells)},
                )
            )
    sug = suggest(upload.dataset, parsed)
    upload.header_fingerprint = sug.fingerprint
    upload.row_count = parsed.row_count
    upload.state = "parsed"
    # Reuse a confirmed mapping for the same entity, dataset and header fingerprint (MH-05).
    reuse = s.execute(
        select(ColumnMapping)
        .join(Upload, Upload.id == ColumnMapping.upload_id)
        .where(
            Upload.entity_id == upload.entity_id,
            Upload.dataset == upload.dataset,
            ColumnMapping.header_fingerprint == sug.fingerprint,
            ColumnMapping.state.in_(("confirmed", "approved")),
        )
        .order_by(ColumnMapping.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if reuse is not None:
        mapping = {**reuse.mapping, "reused_from": str(reuse.id)}
        state, by, at = reuse.state, reuse.confirmed_by, reuse.confirmed_at
    else:
        mapping = {"sheet": sug.sheet, "header_row": sug.header_row, "fields": sug.mapping}
        state, by, at = "draft", None, None
    cm = ColumnMapping(
        firm_id=upload.firm_id,
        upload_id=upload.id,
        version=1,
        header_fingerprint=sug.fingerprint,
        mapping=mapping,
        state=state,
        confirmed_by=by,
        confirmed_at=at,
    )
    if reuse is not None and reuse.state == "approved":
        cm.approved_by, cm.approved_at = reuse.approved_by, reuse.approved_at
    s.add(cm)
    log_event(
        log, "upload.parsed", upload_id=upload.id, rows=parsed.row_count, dataset=upload.dataset
    )


def run_checks(s: Session, c: jobs.Claimed, store: ObjectStore, limits: Limits) -> None:
    run = s.get(CheckRun, uuid.UUID(c.payload["run_id"]))
    if run is None:
        raise readiness.DomainError(404, "run_missing")
    if run.state == "succeeded":
        return
    run.state = "running"
    counts = readiness.execute_run(s, run)
    log_event(
        log,
        "run.succeeded",
        run_id=run.id,
        entity_id=run.entity_id,
        count=counts.failed_blockers + counts.unchecked_blockers,
    )


HANDLERS: dict[str, Callable[[Session, jobs.Claimed, ObjectStore, Limits], None]] = {
    "parse_upload": parse_upload,
    "run_checks": run_checks,
}
