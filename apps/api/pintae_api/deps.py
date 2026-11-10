"""Request context: actor, clock, engine, store. Role checks are server-side (MH-01)."""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import date

from fastapi import Depends, HTTPException, Request
from sqlalchemy import Engine, text

from pintae_core.storage import ObjectStore
from pintae_rules.dates import Clock, dubai_today

DECIDERS = frozenset({"owner", "reviewer"})


@dataclass(frozen=True)
class Actor:
    user_id: uuid.UUID
    firm_id: uuid.UUID
    role: str

    def require(self, roles: frozenset[str]) -> None:
        if self.role not in roles:
            raise HTTPException(status_code=403, detail={"reason": "role_not_permitted"})


def engine(request: Request) -> Engine:
    eng: Engine = request.app.state.engine
    return eng


def store(request: Request) -> ObjectStore:
    st: ObjectStore = request.app.state.store
    return st


def today(request: Request) -> date:
    clock: Clock = request.app.state.clock
    return dubai_today(clock)


def token_hash(token: str) -> bytes:
    return hashlib.sha256(token.encode()).digest()


def actor(request: Request, eng: Engine = Depends(engine)) -> Actor:  # noqa: B008
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail={"reason": "sign_in_required"})
    with eng.begin() as conn:
        row = conn.execute(
            text("SELECT * FROM pintae_resolve_session(:h)"), {"h": token_hash(auth[7:].strip())}
        ).first()
    if row is None:
        raise HTTPException(status_code=401, detail={"reason": "sign_in_required"})
    a = Actor(row.user_id, row.firm_id, row.role)
    request.state.actor = a
    return a
