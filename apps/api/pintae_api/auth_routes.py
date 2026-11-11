"""B2 routes: sign-in, sign-out, invitations, recovery, users (TRD 5.1 Auth, Recovery, Users;
App-flow S-01, S-02, S-15, S-17, S-18). The flows are in ``pintae_core.identity``."""

from __future__ import annotations

import uuid
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import Engine

from pintae_api.deps import (
    SESSION_COOKIE,
    Actor,
    actor,
    client_address,
    engine,
    mailer,
    session_token,
)
from pintae_core import auth, identity, tenancy
from pintae_core.mail import Mailer
from pintae_core.readiness import DomainError
from pintae_rules.dates import Clock

router = APIRouter()

ActorDep = Annotated[Actor, Depends(actor)]
EngineDep = Annotated[Engine, Depends(engine)]
MailerDep = Annotated[Mailer, Depends(mailer)]
OWNER = frozenset({"owner"})


def _set_session(resp: Response, token: str) -> None:
    resp.set_cookie(SESSION_COOKIE, token, secure=True, httponly=True, samesite="lax", path="/")


def _issued(issued: identity.Issued, status_code: int = 200) -> JSONResponse:
    body: dict[str, Any] = {"stage": issued.stage, **issued.extra}
    if issued.stage == "full":
        body["csrf_token"] = issued.csrf
    resp = JSONResponse(status_code=status_code, content=body)
    _set_session(resp, issued.token)
    resp.headers["Cache-Control"] = "no-store"
    return resp


def _now(request: Request) -> Any:
    clock: Clock = request.app.state.clock
    return clock()


class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=1024)


class CodeIn(BaseModel):
    code: str = Field(min_length=1, max_length=32)


class PasswordIn(BaseModel):
    password: str = Field(min_length=1, max_length=1024)


class EmailIn(BaseModel):
    email: str = Field(min_length=3, max_length=254)


class InviteIn(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    role: Literal["owner", "reviewer", "preparer"]


class UserPatchIn(BaseModel):
    role: Literal["owner", "reviewer", "preparer"] | None = None
    disabled: bool | None = None


# --------------------------------------------------------------------------- sign-in (S-01)


@router.post("/auth/login")
def login(body: LoginIn, request: Request, eng: EngineDep) -> JSONResponse:
    return _issued(
        identity.password_step(
            eng, email=body.email, password=body.password, client=client_address(request)
        )
    )


@router.post("/auth/totp")
def totp(body: CodeIn, request: Request, eng: EngineDep) -> JSONResponse:
    return _issued(
        identity.complete_totp(
            eng,
            token=session_token(request),
            code=body.code,
            client=client_address(request),
            now=_now(request),
        )
    )


@router.post("/auth/recovery-code")
def recovery_code(body: CodeIn, request: Request, eng: EngineDep) -> JSONResponse:
    return _issued(
        identity.recovery_step(
            eng, token=session_token(request), code=body.code, client=client_address(request)
        )
    )


@router.get("/auth/session")
def current_session(request: Request, a: ActorDep) -> dict[str, Any]:
    token = session_token(request)
    assert token is not None
    return {
        "user_id": str(a.user_id),
        "firm_id": str(a.firm_id),
        "role": a.role,
        "csrf_token": auth.csrf_token(token),
    }


@router.post("/auth/logout", status_code=204)
def logout(request: Request, a: ActorDep, eng: EngineDep) -> Response:
    identity.logout(eng, session_token(request))
    resp = Response(status_code=204)
    resp.delete_cookie(SESSION_COOKIE, secure=True, httponly=True, samesite="lax", path="/")
    return resp


@router.post("/auth/recovery-codes/regenerate")
def regenerate_codes(a: ActorDep, eng: EngineDep) -> JSONResponse:
    codes = identity.regenerate_recovery_codes(eng, firm_id=a.firm_id, user_id=a.user_id)
    return JSONResponse(content={"recovery_codes": codes}, headers={"Cache-Control": "no-store"})


# --------------------------------------------------------------------------- recovery (S-18)


@router.post("/auth/password-reset", status_code=202)
def password_reset_request(
    body: EmailIn, request: Request, eng: EngineDep, m: MailerDep
) -> dict[str, str]:
    identity.request_reset(eng, m, email=body.email, client=client_address(request))
    return {"status": "if_the_address_has_an_account_a_link_was_sent"}


@router.post("/auth/password-reset/{token}")
def password_reset_complete(
    token: str, body: PasswordIn, request: Request, eng: EngineDep
) -> JSONResponse:
    return _issued(
        identity.complete_reset(
            eng, token=token, password=body.password, client=client_address(request)
        )
    )


# --------------------------------------------------------------------------- invitations (S-02)


@router.post("/invites", status_code=201)
def create_invite(body: InviteIn, a: ActorDep, eng: EngineDep, m: MailerDep) -> dict[str, str]:
    a.require(OWNER)
    iid = identity.create_invite(
        eng, m, firm_id=a.firm_id, actor_id=a.user_id, email=body.email, role=body.role
    )
    return {"id": str(iid)}


@router.get("/invites/{token}")
def invite_info(token: str, eng: EngineDep) -> dict[str, Any]:
    return identity.invite_info(eng, token)


@router.post("/invites/{token}/accept")
def accept_invite(token: str, body: PasswordIn, request: Request, eng: EngineDep) -> JSONResponse:
    return _issued(
        identity.accept_invite(
            eng, token=token, password=body.password, client=client_address(request)
        )
    )


# --------------------------------------------------------------------------- users (S-15)


@router.get("/users")
def list_users(a: ActorDep, eng: EngineDep) -> dict[str, Any]:
    a.require(OWNER)
    with tenancy.session(a.firm_id, eng) as s:
        return {"items": identity.list_users(s)}


@router.patch("/users/{user_id}")
def patch_user(
    user_id: uuid.UUID, body: UserPatchIn, a: ActorDep, eng: EngineDep
) -> dict[str, Any]:
    a.require(OWNER)
    if body.role is None and body.disabled is None:
        raise DomainError(422, "nothing_to_change")
    return identity.update_user(
        eng,
        firm_id=a.firm_id,
        actor_id=a.user_id,
        user_id=user_id,
        role=body.role,
        disabled=body.disabled,
    )
