"""FastAPI application (TRD section 5.1, prefix /api/v1). B1: the core path only.

Conventions: unknown or foreign identifiers return 404 and write an audit event; a stale
version pin returns 409 with the current versions; validation errors return 422; long work
returns 202 with a job identifier; every request carries a correlation identifier.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import urlparse

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError

from pintae_api import auth_routes, routes
from pintae_core import audit, readiness, tenancy
from pintae_core.config import get_settings
from pintae_core.db import app_engine
from pintae_core.idempotency import IdempotencyConflict
from pintae_core.logging import configure_logging, correlation_id_var, log_event, new_correlation_id
from pintae_core.mail import Mailer, default_mailer
from pintae_core.models import SCHEMA_REVISION
from pintae_core.readiness import DomainError
from pintae_core.storage import ObjectStore, default_store
from pintae_rules.dates import Clock, utc_now

log = logging.getLogger("pintae.api")


def create_app(
    engine: Engine | None = None,
    store: ObjectStore | None = None,
    clock: Clock | None = None,
    mailer: Mailer | None = None,
) -> FastAPI:
    configure_logging()
    app = FastAPI(title="PINT AE Readiness Desk API", version="0.2.0-b2")
    app.state.engine = engine or app_engine()
    app.state.store = store or default_store()
    app.state.clock = clock or utc_now
    app.state.mailer = mailer or default_mailer()
    app.include_router(routes.router, prefix="/api/v1")
    app.include_router(auth_routes.router, prefix="/api/v1")
    allowed_origin = _origin(get_settings().public_base_url)

    @app.middleware("http")
    async def same_origin(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """A state-changing request that names another origin is refused (defence in depth
        next to SameSite=Lax and the anti-forgery token, ASVS 3.5.1)."""
        origin = request.headers.get("origin")
        unsafe = request.method not in ("GET", "HEAD", "OPTIONS")
        if unsafe and origin is not None and origin != allowed_origin:
            return JSONResponse(status_code=403, content={"reason": "cross_origin_refused"})
        return await call_next(request)

    @app.middleware("http")
    async def correlation(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        incoming = request.headers.get("x-correlation-id")
        try:
            cid = str(uuid.UUID(incoming)) if incoming else new_correlation_id()
        except ValueError:
            cid = new_correlation_id()
        token = correlation_id_var.set(cid)
        started = time.monotonic()
        try:
            response = await call_next(request)
        finally:
            correlation_id_var.reset(token)
        response.headers["X-Correlation-ID"] = cid
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; object-src 'none'; base-uri 'none'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers.setdefault("Cache-Control", "no-store")
        response.headers["Referrer-Policy"] = "no-referrer"
        token = correlation_id_var.set(cid)
        log_event(
            log,
            "http.request",
            method=request.method,
            route=request.scope.get("route").path if request.scope.get("route") else "unmatched",  # type: ignore[union-attr]
            status_code=response.status_code,
            duration_ms=int((time.monotonic() - started) * 1000),
        )
        correlation_id_var.reset(token)
        return response

    @app.exception_handler(DomainError)
    async def domain_error(request: Request, exc: DomainError) -> JSONResponse:
        if exc.code == 404:
            _audit_not_found(request, exc)
        body: dict[str, Any] = {"reason": exc.reason, **exc.detail}
        if exc.code == 404:  # never echo what was looked for
            body = {"reason": "not_found"}
        return JSONResponse(status_code=exc.code, content=body)

    @app.exception_handler(IntegrityError)
    async def integrity(request: Request, exc: IntegrityError) -> JSONResponse:
        constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
        return JSONResponse(
            status_code=409, content={"reason": "conflict", "constraint": constraint}
        )

    @app.exception_handler(IdempotencyConflict)
    async def idem_conflict(request: Request, exc: IdempotencyConflict) -> JSONResponse:
        return JSONResponse(
            status_code=422, content={"reason": "idempotency_key_reused_with_different_request"}
        )

    @app.exception_handler(RequestValidationError)
    async def validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {"path": ".".join(str(p) for p in e["loc"]), "type": e["type"]} for e in exc.errors()
        ]
        return JSONResponse(
            status_code=422, content={"reason": "validation_failed", "errors": errors}
        )

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, dict) else {"reason": str(exc.detail)}
        return JSONResponse(status_code=exc.status_code, content=detail)

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    def readyz() -> JSONResponse:
        checks = readiness_checks(app.state.engine, app.state.store)
        ok = all(v == "ok" for v in checks.values())
        return JSONResponse(status_code=200 if ok else 503, content={"ready": ok, "checks": checks})

    return app


def _origin(url: str) -> str:
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}"


def readiness_checks(engine: Engine, store: ObjectStore) -> dict[str, str]:
    """Database, migrations, storage and worker heartbeat (OPS-04, R-17)."""
    checks: dict[str, str] = {}
    max_age = get_settings().worker_heartbeat_max_age_seconds

    def probe(name: str, sql: str, params: dict[str, Any], ok: Callable[[Any], str]) -> None:
        try:
            with engine.connect() as conn:
                checks[name] = ok(conn.execute(text(sql), params).scalar_one_or_none())
        except Exception as exc:
            checks[name] = f"failed ({type(exc).__name__})"

    probe("database", "SELECT 1", {}, lambda v: "ok")
    probe(
        "migrations",
        "SELECT version_num FROM alembic_version",
        {},
        lambda v: "ok" if v == SCHEMA_REVISION else f"at {v}, expected {SCHEMA_REVISION}",
    )
    probe(
        "worker",
        "SELECT count(*) FROM worker_heartbeats WHERE seen_at > now() - make_interval(secs => :s)",
        {"s": max_age},
        lambda v: "ok" if v else "no heartbeat",
    )
    try:  # B1-012: the reference data in force loads and matches its content hash
        with tenancy.reference_session(engine) as s:
            readiness.current_calendar(s)
            unverified = readiness.newest_calendar_unverified(s)
            if unverified is not None:
                raise DomainError(503, f"newest_calendar_unverified:{unverified}")
            readiness.current_pack(s, readiness.now_dubai_date(utc_now()))
        checks["reference_data"] = "ok"
    except DomainError as exc:
        checks["reference_data"] = f"failed ({exc.reason})"
    except Exception as exc:
        checks["reference_data"] = f"failed ({type(exc).__name__})"
    checks["storage"] = "ok" if store.writable() else "not writable"
    return checks


def _audit_not_found(request: Request, exc: DomainError) -> None:
    actor = getattr(request.state, "actor", None)
    if actor is None:
        return
    raw = exc.detail.get("object_id")
    try:
        oid = uuid.UUID(str(raw)) if raw else None
    except ValueError:
        oid = None
    try:
        with tenancy.session(actor.firm_id, request.app.state.engine) as s:
            audit.record(
                s,
                firm_id=actor.firm_id,
                action="access.not_found",
                object_type=str(exc.detail.get("object_type", "unknown")),
                object_id=oid,
                actor_id=actor.user_id,
                detail={"route": request.url.path.split("?")[0].rsplit("/", 1)[0]},
            )
    except Exception:  # an audit failure must not turn a 404 into a 500
        log_event(log, "audit.write_failed", logging.ERROR, reason_code="not_found_audit")


def app() -> FastAPI:  # uvicorn factory: `uvicorn pintae_api.main:app --factory`
    return create_app()
