"""Request context: actor, clock, engine, store. Role checks are server-side (MH-01)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date

from fastapi import Depends, HTTPException, Request
from sqlalchemy import Engine

from pintae_core import auth, identity
from pintae_core.mail import Mailer
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


SESSION_COOKIE = "__Host-pintae_session"  # Secure, HttpOnly, SameSite=Lax, Path=/ (TRD 8.1)
CSRF_HEADER = "x-csrf-token"
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def mailer(request: Request) -> Mailer:
    m: Mailer = request.app.state.mailer
    return m


def client_address(request: Request) -> str:
    """The peer address. Forwarding headers are not trusted here (TRD 8.8, 4.1.3)."""
    return request.client.host if request.client else "unknown"


def session_token(request: Request) -> str | None:
    return request.cookies.get(SESSION_COOKIE)


def actor(request: Request, eng: Engine = Depends(engine)) -> Actor:  # noqa: B008
    """A signed-in user: a ``full`` session from the cookie, and on every state-changing
    request the anti-forgery token in the X-CSRF-Token header (ASVS 3.5.1)."""
    token = session_token(request)
    rs = identity.resolve(eng, token)
    if rs is None or rs.stage != "full" or token is None:
        raise HTTPException(status_code=401, detail={"reason": "sign_in_required"})
    if request.method not in SAFE_METHODS and not auth.csrf_ok(
        token, request.headers.get(CSRF_HEADER)
    ):
        raise HTTPException(status_code=403, detail={"reason": "anti_forgery_token_invalid"})
    a = Actor(rs.user_id, rs.firm_id, rs.role)
    request.state.actor = a
    return a
