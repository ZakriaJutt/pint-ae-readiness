"""Idempotency keys for mutating requests (TRD section 5.1 conventions)."""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from pintae_core.models import IdempotencyKey

TTL = timedelta(hours=48)  # schema.md section 6, class D


class IdempotencyConflict(Exception):
    pass


def request_hash(*parts: bytes | str) -> bytes:
    h = hashlib.sha256()
    for p in parts:
        h.update(p if isinstance(p, bytes) else p.encode())
        h.update(b"\x1f")
    return h.digest()


def lookup(
    s: Session, firm_id: uuid.UUID, route: str, key: str, rhash: bytes
) -> dict[str, Any] | None:
    row = s.execute(
        select(IdempotencyKey).where(
            IdempotencyKey.firm_id == firm_id,
            IdempotencyKey.route == route,
            IdempotencyKey.key == key,
        )
    ).scalar_one_or_none()
    if row is None:
        return None
    if row.expires_at < datetime.now(tz=UTC):
        s.delete(row)
        s.flush()
        return None
    if row.request_hash != rhash:
        raise IdempotencyConflict(key)
    return dict(row.response)


def remember(
    s: Session, firm_id: uuid.UUID, route: str, key: str, rhash: bytes, response: dict[str, Any]
) -> None:
    s.add(
        IdempotencyKey(
            firm_id=firm_id,
            route=route,
            key=key,
            request_hash=rhash,
            response=response,
            expires_at=datetime.now(tz=UTC) + TTL,
        )
    )
