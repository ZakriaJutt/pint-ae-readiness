"""Structured JSON logging with correlation identifiers (TRD 8.7, R-07, R-12).

No web-framework imports here: the worker uses this module too. Only allow-listed fields
are emitted; free-text messages are event names, never cell values, names or TRNs.
"""

from __future__ import annotations

import contextvars
import json
import logging
import sys
import uuid
from datetime import UTC, datetime
from typing import Any

correlation_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "correlation_id", default=None
)

# Identifiers and counts only (IT-10). Anything else passed as a field is dropped.
ALLOWED_FIELDS = frozenset(
    {
        "firm_id",
        "entity_id",
        "upload_id",
        "run_id",
        "job_id",
        "job_kind",
        "attempt_id",
        "report_id",
        "user_id",
        "status_code",
        "method",
        "route",
        "duration_ms",
        "rows",
        "findings",
        "count",
        "dataset",
        "state",
        "reason_code",
        "rule_pack",
        "service",
        "worker_id",
    }
)


def new_correlation_id() -> str:
    return str(uuid.uuid4())


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
            "correlation_id": correlation_id_var.get(),
        }
        fields = getattr(record, "fields", None)
        if isinstance(fields, dict):
            for key, value in fields.items():
                if key in ALLOWED_FIELDS:
                    payload[key] = value if isinstance(value, int | float | bool) else str(value)
        if record.exc_info and record.exc_info[0] is not None:
            # Exception type only: messages can carry cell values.
            payload["error_type"] = record.exc_info[0].__name__
        return json.dumps(payload, sort_keys=True)


def configure_logging(level: int = logging.INFO) -> None:
    root = logging.getLogger()
    if any(getattr(h, "_pintae", False) for h in root.handlers):
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler._pintae = True  # type: ignore[attr-defined]
    root.addHandler(handler)
    root.setLevel(level)


def log_event(logger: logging.Logger, event: str, level: int = logging.INFO, **fields: Any) -> None:
    logger.log(level, event, extra={"fields": fields})
