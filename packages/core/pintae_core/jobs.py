"""Jobs in PostgreSQL (AD-02, TRD 6.3, T-2.2.5, R-01, R-02).

Claiming crosses firms, so it goes through the security-definer ``pintae_claim_job``; every
read or write of job results then happens inside the job firm's tenancy session. Only the
holder of the current ``attempt_id`` may write a result; a superseded attempt's completion
is discarded and logged.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from sqlalchemy import Engine, select, text, update
from sqlalchemy.orm import Session

from pintae_core.logging import correlation_id_var, log_event, new_correlation_id
from pintae_core.models import Job

log = logging.getLogger("pintae.jobs")

MAX_ATTEMPTS = {"parse_upload": 4, "run_checks": 3}
BACKOFF_SECONDS = {1: 30, 2: 120, 3: 600}


class SupersededAttempt(Exception):
    pass


@dataclass(frozen=True)
class Claimed:
    job_id: uuid.UUID
    firm_id: uuid.UUID
    kind: str
    payload: dict[str, Any]
    attempt_id: uuid.UUID
    state_version: int
    correlation_id: uuid.UUID
    attempts: int


def enqueue(s: Session, *, firm_id: uuid.UUID, kind: str, payload: dict[str, Any]) -> Job:
    cid = correlation_id_var.get() or new_correlation_id()
    job = Job(
        firm_id=firm_id,
        kind=kind,
        payload=payload,
        state="queued",
        correlation_id=uuid.UUID(cid),
    )
    s.add(job)
    s.flush()
    return job


def claim(engine: Engine, lease_seconds: int) -> Claimed | None:
    with engine.begin() as conn:
        row = conn.execute(text("SELECT * FROM pintae_claim_job(:l)"), {"l": lease_seconds}).first()
    if row is None:
        return None
    return Claimed(
        job_id=row.job_id,
        firm_id=row.firm_id,
        kind=row.kind,
        payload=dict(row.payload),
        attempt_id=row.attempt_id,
        state_version=row.state_version,
        correlation_id=row.correlation_id,
        attempts=row.attempts,
    )


def requeue_expired(engine: Engine) -> int:
    with engine.begin() as conn:
        n = conn.execute(text("SELECT pintae_requeue_expired()")).scalar_one()
    return int(n)


def lock_current_attempt(s: Session, c: Claimed) -> Job:
    """Inside the firm's session: lock the job row if this attempt still holds it."""
    job = s.execute(
        select(Job)
        .where(Job.id == c.job_id, Job.attempt_id == c.attempt_id, Job.state == "running")
        .with_for_update()
    ).scalar_one_or_none()
    if job is None:
        log_event(
            log,
            "job.completion_discarded",
            logging.WARNING,
            job_id=c.job_id,
            attempt_id=c.attempt_id,
            reason_code="superseded_attempt",
        )
        raise SupersededAttempt(str(c.job_id))
    return job


def mark_succeeded(s: Session, c: Claimed) -> None:
    res = s.execute(
        update(Job)
        .where(
            Job.id == c.job_id,
            Job.attempt_id == c.attempt_id,
            Job.state == "running",
        )
        .values(state="succeeded", state_version=Job.state_version + 1, lease_expires_at=None)
    )
    if res.rowcount != 1:  # type: ignore[attr-defined]
        raise SupersededAttempt(str(c.job_id))


def mark_failed_or_retry(s: Session, c: Claimed, error_code: str, *, retryable: bool = True) -> str:
    """Compare-and-set: never regresses a job another attempt already moved on."""
    budget = MAX_ATTEMPTS.get(c.kind, 4)
    if retryable and c.attempts < budget:
        delay = timedelta(seconds=BACKOFF_SECONDS.get(c.attempts, 600))
        values: dict[str, Any] = {
            "state": "queued",
            "attempt_id": None,
            "lease_expires_at": None,
            "run_after": text(f"now() + interval '{int(delay.total_seconds())} seconds'"),
        }
        new_state = "queued"
    else:
        values = {"state": "failed", "lease_expires_at": None}
        new_state = "failed"
    res = s.execute(
        update(Job)
        .where(Job.id == c.job_id, Job.attempt_id == c.attempt_id, Job.state == "running")
        .values(state_version=Job.state_version + 1, last_error_code=error_code, **values)
    )
    if res.rowcount != 1:  # type: ignore[attr-defined]
        log_event(
            log,
            "job.completion_discarded",
            logging.WARNING,
            job_id=c.job_id,
            attempt_id=c.attempt_id,
            reason_code="superseded_attempt",
        )
        return "discarded"
    return new_state


def heartbeat(engine: Engine, worker_id: str) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO worker_heartbeats (worker_id, seen_at) VALUES (:w, now()) "
                "ON CONFLICT (worker_id) DO UPDATE SET seen_at = excluded.seen_at"
            ),
            {"w": worker_id},
        )
