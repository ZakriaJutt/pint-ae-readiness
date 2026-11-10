"""Append-only audit events (TRD 8.6). Identifiers and versions only, never cell values."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from pintae_core.logging import correlation_id_var
from pintae_core.models import AuditEvent


def record(
    s: Session,
    *,
    firm_id: uuid.UUID,
    action: str,
    object_type: str,
    object_id: uuid.UUID | None,
    actor_id: uuid.UUID | None,
    actor_kind: str = "user",
    detail: dict[str, Any] | None = None,
) -> None:
    cid = correlation_id_var.get()
    s.add(
        AuditEvent(
            firm_id=firm_id,
            actor_id=actor_id,
            actor_kind=actor_kind,
            action=action,
            object_type=object_type,
            object_id=object_id,
            detail=detail or {},
            correlation_id=uuid.UUID(cid) if cid else uuid.uuid4(),
        )
    )
