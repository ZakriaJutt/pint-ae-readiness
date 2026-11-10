"""Worker entry point (TRD section 6.3). Imports no web framework (R-07, ARCH-01).

``python -m pintae_worker.main`` runs the loop; ``run_once`` processes one job (tests).
"""

from __future__ import annotations

import logging
import os
import signal
import socket
import time

from sqlalchemy import Engine

from pintae_core import jobs, tenancy
from pintae_core.config import get_settings
from pintae_core.db import app_engine
from pintae_core.logging import configure_logging, correlation_id_var, log_event
from pintae_core.readiness import DomainError
from pintae_core.storage import ObjectStore, default_store
from pintae_ingest.parsers import Limits
from pintae_worker.handlers import HANDLERS

log = logging.getLogger("pintae.worker")
_stop = False


def _limits() -> Limits:
    cfg = get_settings()
    return Limits(cfg.max_upload_bytes, cfg.max_xlsx_uncompressed_bytes, cfg.max_rows)


def process(engine: Engine, store: ObjectStore, claimed: jobs.Claimed) -> str:
    token = correlation_id_var.set(str(claimed.correlation_id))
    try:
        handler = HANDLERS.get(claimed.kind)
        try:
            with tenancy.session(claimed.firm_id, engine) as s:
                jobs.lock_current_attempt(s, claimed)
                if handler is None:
                    raise DomainError(500, "unknown_job_kind")
                handler(s, claimed, store, _limits())
                jobs.mark_succeeded(s, claimed)
            log_event(
                log,
                "job.succeeded",
                job_id=claimed.job_id,
                job_kind=claimed.kind,
                attempt_id=claimed.attempt_id,
            )
            return "succeeded"
        except jobs.SupersededAttempt:
            return "discarded"
        except Exception as exc:
            code = exc.reason if isinstance(exc, DomainError) else type(exc).__name__
            log_event(
                log,
                "job.failed",
                logging.ERROR,
                job_id=claimed.job_id,
                job_kind=claimed.kind,
                attempt_id=claimed.attempt_id,
                reason_code=code,
            )
            with tenancy.session(claimed.firm_id, engine) as s:
                return jobs.mark_failed_or_retry(s, claimed, code)
    finally:
        correlation_id_var.reset(token)


def run_once(engine: Engine | None = None, store: ObjectStore | None = None) -> str | None:
    eng = engine or app_engine()
    claimed = jobs.claim(eng, get_settings().job_lease_seconds)
    if claimed is None:
        return None
    return process(eng, store or default_store(), claimed)


def _handle_stop(signum: int, frame: object) -> None:
    global _stop
    _stop = True


def main() -> None:
    configure_logging()
    signal.signal(signal.SIGTERM, _handle_stop)
    signal.signal(signal.SIGINT, _handle_stop)
    eng = app_engine()
    store = default_store()
    worker_id = f"{socket.gethostname()}:{os.getpid()}"
    log_event(log, "worker.started", worker_id=worker_id, service="worker")
    last_beat = 0.0
    while not _stop:
        now = time.monotonic()
        if now - last_beat >= 5:
            jobs.heartbeat(eng, worker_id)
            jobs.requeue_expired(eng)
            last_beat = now
        claimed = jobs.claim(eng, get_settings().job_lease_seconds)
        if claimed is None:
            time.sleep(0.5)
            continue
        process(eng, store, claimed)
    log_event(log, "worker.stopped", worker_id=worker_id, service="worker")


if __name__ == "__main__":
    main()
