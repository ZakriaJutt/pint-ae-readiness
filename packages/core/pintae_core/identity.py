"""Sign-in flows (TRD 8.1, App-flow S-01, S-02, S-15, S-17, S-18; B2).

Password plus TOTP for every user. Invitations are single-use activation codes valid 24 hours;
e-mail is never an authentication factor. Sessions are opaque server-side tokens in the
``sessions`` table, with stages: ``password`` (TOTP or recovery code pending), ``enrol`` (TOTP
enrolment pending) and ``full``. Only ``full`` reaches application routes. The token changes
when a session becomes ``full`` (ASVS 7.2.4). Times that decide expiry are the database's.

Every database access goes through ``tenancy``: ``global_session`` for the steps before a
firm is known (security-definer lookups and the throttle), ``session(firm_id)`` otherwise.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy import Engine, delete, func, select, text, update
from sqlalchemy.orm import Session

from pintae_core import audit, auth, tenancy
from pintae_core.config import get_settings
from pintae_core.mail import Mailer, invite_message, reset_message
from pintae_core.models import (
    AuthAttempt,
    Firm,
    Invite,
    PasswordReset,
    RecoveryCode,
    SessionRow,
    User,
)
from pintae_core.readiness import DomainError

ROLES = ("owner", "reviewer", "preparer")
SIGN_IN_FAILED = "sign_in_failed"  # one generic reason: never which part failed (S-01)


@dataclass
class Issued:
    """A session token for the cookie, its stage, and what the next screen needs."""

    token: str
    stage: str
    firm_id: uuid.UUID
    user_id: uuid.UUID
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def csrf(self) -> str:
        return auth.csrf_token(self.token)


@dataclass(frozen=True)
class ResolvedSession:
    session_id: uuid.UUID
    user_id: uuid.UUID
    firm_id: uuid.UUID
    role: str
    stage: str


# --------------------------------------------------------------------------- throttle


def _throttle_check(s: Session, keys: list[tuple[bytes, str]]) -> None:
    """ASVS 6.3.1: refuse with 429 once a client address has made too many sign-in requests,
    or an account has too many failures since its last success, within the window."""
    cfg = get_settings()
    since = text(f"now() - interval '{int(cfg.throttle_window_minutes)} minutes'")
    for key, kind in keys:
        q = (
            select(func.count())
            .select_from(AuthAttempt)
            .where(AuthAttempt.key_hash == key, AuthAttempt.at > since)
        )
        if kind == "account":
            last_ok = (
                select(func.max(AuthAttempt.at))
                .where(AuthAttempt.key_hash == key, AuthAttempt.succeeded.is_(True))
                .scalar_subquery()
            )
            q = q.where(
                AuthAttempt.succeeded.is_(False),
                AuthAttempt.at > func.coalesce(last_ok, text("'-infinity'::timestamptz")),
            )
            limit = cfg.throttle_account_failures
        else:
            limit = cfg.throttle_client_attempts
        if s.execute(q).scalar_one() >= limit:
            raise DomainError(
                429, "too_many_attempts", {"retry_after_minutes": cfg.throttle_window_minutes}
            )


def _record(eng: Engine, keys: list[tuple[bytes, str]], ok: bool) -> None:
    with tenancy.global_session(eng) as s:
        for key, kind in keys:
            s.add(AuthAttempt(key_hash=key, kind=kind, succeeded=ok))


def _client_key(client: str) -> tuple[bytes, str]:
    return auth.throttle_key("client", client or "unknown"), "client"


def _account_key(value: str) -> tuple[bytes, str]:
    return auth.throttle_key("account", value), "account"


# --------------------------------------------------------------------------- sessions


def resolve(eng: Engine, token: str | None) -> ResolvedSession | None:
    if not token:
        return None
    with tenancy.global_session(eng) as s:
        row = s.execute(
            text("SELECT * FROM pintae_resolve_session(:h)"), {"h": auth.token_hash(token)}
        ).first()
    if row is None:
        return None
    return ResolvedSession(row.session_id, row.user_id, row.firm_id, row.role, row.stage)


def _new_session(s: Session, user: User, stage: str) -> str:
    cfg = get_settings()
    token = auth.new_token()
    minutes = cfg.session_pending_minutes if stage != "full" else cfg.session_absolute_hours * 60
    s.add(
        SessionRow(
            firm_id=user.firm_id,
            user_id=user.id,
            token_hash=auth.token_hash(token),
            last_seen_at=func.now(),
            absolute_expires_at=func.now() + text(f"interval '{int(minutes)} minutes'"),
            stage=stage,
        )
    )
    return token


def _promote(s: Session, sess_id: uuid.UUID, stage: str) -> str:
    """Move a pending session on: a new token every time (ASVS 7.2.4)."""
    cfg = get_settings()
    token = auth.new_token()
    minutes = cfg.session_pending_minutes if stage != "full" else cfg.session_absolute_hours * 60
    s.execute(
        update(SessionRow)
        .where(SessionRow.id == sess_id)
        .values(
            token_hash=auth.token_hash(token),
            stage=stage,
            failed_codes=0,
            last_seen_at=func.now(),
            absolute_expires_at=func.now() + text(f"interval '{int(minutes)} minutes'"),
        )
    )
    return token


def _end_sessions(s: Session, user_id: uuid.UUID) -> int:
    res = s.execute(
        update(SessionRow)
        .where(SessionRow.user_id == user_id, SessionRow.ended_at.is_(None))
        .values(ended_at=func.now())
    )
    return int(res.rowcount)  # type: ignore[attr-defined]


def logout(eng: Engine, token: str | None) -> bool:
    rs = resolve(eng, token)
    if rs is None:
        return False
    with tenancy.session(rs.firm_id, eng) as s:
        s.execute(
            update(SessionRow).where(SessionRow.id == rs.session_id).values(ended_at=func.now())
        )
        audit.record(
            s,
            firm_id=rs.firm_id,
            action="auth.signed_out",
            object_type="user",
            object_id=rs.user_id,
            actor_id=rs.user_id,
        )
    return True


def _pending(eng: Engine, token: str | None, stages: tuple[str, ...]) -> ResolvedSession:
    rs = resolve(eng, token)
    if rs is None or rs.stage not in stages:
        raise DomainError(401, "sign_in_required")
    return rs


def _enrolment(s: Session, user: User) -> dict[str, Any]:
    """A fresh TOTP secret for a user whose enrolment is not confirmed."""
    secret = auth.new_totp_secret()
    user.totp_secret_enc = auth.seal_totp_secret(secret, user.id)
    user.totp_confirmed_at = None
    user.totp_last_step = None
    return {
        "totp_secret": auth.totp_secret_b32(secret),
        "otpauth_uri": auth.otpauth_uri(secret, user.email),
    }


# --------------------------------------------------------------------------- invitations


def _user_exists(eng: Engine, email: str) -> bool:
    with tenancy.global_session(eng) as s:
        return (
            s.execute(text("SELECT 1 FROM pintae_login_lookup(:e)"), {"e": email}).first()
            is not None
        )


def create_invite(
    eng: Engine,
    mailer: Mailer,
    *,
    firm_id: uuid.UUID,
    actor_id: uuid.UUID | None,
    email: str,
    role: str,
) -> uuid.UUID:
    """Owner invites staff (S-15); also used by the vendor onboarding script for a firm's
    first Owner. An open invitation for the same address is revoked."""
    cfg = get_settings()
    if role not in ROLES:
        raise DomainError(422, "unknown_role")
    email = email.strip()
    if "@" not in email or len(email) > 254:
        raise DomainError(422, "invalid_email")
    if _user_exists(eng, email):
        raise DomainError(409, "email_in_use")
    token = auth.new_token()
    with tenancy.session(firm_id, eng) as s:
        firm = s.get(Firm, firm_id)
        if firm is None:
            raise DomainError(404, "not_found", {"object_type": "firm", "object_id": str(firm_id)})
        s.execute(
            update(Invite)
            .where(Invite.email == email, Invite.used_at.is_(None), Invite.revoked_at.is_(None))
            .values(revoked_at=func.now())
        )
        inv = Invite(
            firm_id=firm_id,
            created_by=actor_id,
            email=email,
            role=role,
            token_hash=auth.token_hash(token),
            expires_at=func.now() + text(f"interval '{int(cfg.invite_valid_hours)} hours'"),
        )
        s.add(inv)
        s.flush()
        audit.record(
            s,
            firm_id=firm_id,
            action="user.invited",
            object_type="invite",
            object_id=inv.id,
            actor_id=actor_id,
            actor_kind="user" if actor_id else "vendor",
            detail={"role": role},
        )
        firm_name, invite_id = firm.legal_name, inv.id
    link = f"{cfg.public_base_url.rstrip('/')}/invite/{token}"
    mailer.send(invite_message(email, firm_name, role, link, cfg.invite_valid_hours))
    return invite_id


def _token_firm(eng: Engine, kind: str, token: str) -> uuid.UUID | None:
    with tenancy.global_session(eng) as s:
        fid: uuid.UUID | None = s.execute(
            text("SELECT pintae_token_firm(:k, :h)"), {"k": kind, "h": auth.token_hash(token)}
        ).scalar_one()
    return fid


def invite_info(eng: Engine, token: str) -> dict[str, Any]:
    fid = _token_firm(eng, "invite", token)
    if fid is None:
        raise DomainError(410, "invite_invalid_or_expired")
    with tenancy.session(fid, eng) as s:
        inv = _open_invite(s, token)
        firm = s.get(Firm, fid)
        assert firm is not None
        return {"firm": firm.legal_name, "role": inv.role, "email": inv.email}


def _open_invite(s: Session, token: str) -> Invite:
    inv = s.execute(
        select(Invite)
        .where(
            Invite.token_hash == auth.token_hash(token),
            Invite.used_at.is_(None),
            Invite.revoked_at.is_(None),
            Invite.expires_at > func.now(),
        )
        .with_for_update()
    ).scalar_one_or_none()
    if inv is None:
        raise DomainError(410, "invite_invalid_or_expired")
    return inv


def accept_invite(eng: Engine, *, token: str, password: str, client: str) -> Issued:
    """S-02 step 1: the invitee chooses a password; the invitation is used up and a TOTP
    secret is issued for enrolment. Step 2 is ``complete_totp`` on the ``enrol`` session."""
    keys = [_client_key(client)]
    with tenancy.global_session(eng) as s:
        _throttle_check(s, keys)
    _record(eng, keys, True)
    fid = _token_firm(eng, "invite", token)
    if fid is None:
        raise DomainError(410, "invite_invalid_or_expired")
    with tenancy.session(fid, eng) as s:
        inv = _open_invite(s, token)
        problems = auth.password_problems(password, inv.email)
        if problems:
            raise DomainError(422, "password_refused", {"problems": problems})
        if _user_exists(eng, inv.email):
            raise DomainError(409, "email_in_use")
        uid = uuid.uuid4()
        user = User(
            id=uid,
            firm_id=fid,
            email=inv.email,
            role=inv.role,
            password_hash=auth.hash_password(password),
            totp_secret_enc=b"",
        )
        extra = _enrolment(s, user)
        s.add(user)
        inv.used_at = func.now()
        s.flush()
        sess = _new_session(s, user, "enrol")
        audit.record(
            s,
            firm_id=fid,
            action="user.invite_accepted",
            object_type="user",
            object_id=uid,
            actor_id=uid,
            detail={"role": inv.role},
        )
        return Issued(sess, "enrol", fid, uid, extra)


# --------------------------------------------------------------------------- sign-in


def password_step(eng: Engine, *, email: str, password: str, client: str) -> Issued:
    """S-01 step 1. The same generic refusal whether the address, the password or the
    account state was wrong."""
    email = email.strip()
    keys = [_client_key(client), _account_key(email)]
    with tenancy.global_session(eng) as s:
        _throttle_check(s, keys)
        row = s.execute(text("SELECT * FROM pintae_login_lookup(:e)"), {"e": email}).first()
    if row is None:
        auth.burn_password_check(password)
        _record(eng, keys, False)
        raise DomainError(401, SIGN_IN_FAILED)
    ok = auth.verify_password(password, row.password_hash) and not row.disabled
    _record(eng, [keys[0]], True)
    _record(eng, [keys[1]], ok)
    if not ok:
        _audit_failure(eng, row.firm_id, row.user_id, "password")
        raise DomainError(401, SIGN_IN_FAILED)
    with tenancy.session(row.firm_id, eng) as s:
        user = s.get(User, row.user_id)
        assert user is not None
        if user.totp_confirmed_at is None:
            extra = _enrolment(s, user)
            return Issued(_new_session(s, user, "enrol"), "enrol", user.firm_id, user.id, extra)
        return Issued(_new_session(s, user, "password"), "password", user.firm_id, user.id)


def _audit_failure(eng: Engine, firm_id: uuid.UUID, user_id: uuid.UUID, step: str) -> None:
    with tenancy.session(firm_id, eng) as s:
        audit.record(
            s,
            firm_id=firm_id,
            action="auth.sign_in_failed",
            object_type="user",
            object_id=user_id,
            actor_id=None,
            detail={"step": step},
        )


def _code_failed(eng: Engine, rs: ResolvedSession) -> None:
    cfg = get_settings()
    with tenancy.session(rs.firm_id, eng) as s:
        sess = s.get(SessionRow, rs.session_id)
        assert sess is not None
        sess.failed_codes += 1
        if sess.failed_codes >= cfg.totp_failures_per_session:
            sess.ended_at = func.now()
    _record(eng, [_account_key(str(rs.user_id))], False)
    _audit_failure(eng, rs.firm_id, rs.user_id, "code")


def complete_totp(
    eng: Engine, *, token: str | None, code: str, client: str, now: datetime
) -> Issued:
    """S-01 step 2 (``password`` session) or S-02 step 2 (``enrol`` session). Enrolment
    issues ten recovery codes, shown once."""
    rs = _pending(eng, token, ("password", "enrol"))
    keys = [_client_key(client), _account_key(str(rs.user_id))]
    with tenancy.global_session(eng) as s:
        _throttle_check(s, keys)
    _record(eng, [keys[0]], True)
    with tenancy.session(rs.firm_id, eng) as s:
        user = s.get(User, rs.user_id, with_for_update=True)
        assert user is not None
        secret = auth.open_totp_secret(user.totp_secret_enc, user.id)
        step = auth.verify_totp(secret, code, now, user.totp_last_step) if secret else None
        if step is None:
            ok = False
        else:
            ok = True
            user.totp_last_step = step
            extra: dict[str, Any] = {}
            if rs.stage == "enrol":
                user.totp_confirmed_at = func.now()
                extra["recovery_codes"] = _issue_recovery_codes(s, user)
            new = _promote(s, rs.session_id, "full")
            audit.record(
                s,
                firm_id=rs.firm_id,
                action="auth.totp_enrolled" if rs.stage == "enrol" else "auth.signed_in",
                object_type="user",
                object_id=user.id,
                actor_id=user.id,
            )
    if not ok:
        _code_failed(eng, rs)
        raise DomainError(401, SIGN_IN_FAILED)
    _record(eng, [keys[1]], True)
    return Issued(new, "full", rs.firm_id, rs.user_id, extra)


def recovery_step(eng: Engine, *, token: str | None, code: str, client: str) -> Issued:
    """S-18 (b): a single-use recovery code instead of the TOTP code, then forced
    re-enrolment: the session moves to ``enrol`` with a new TOTP secret."""
    rs = _pending(eng, token, ("password",))
    keys = [_client_key(client), _account_key(str(rs.user_id))]
    with tenancy.global_session(eng) as s:
        _throttle_check(s, keys)
    _record(eng, [keys[0]], True)
    with tenancy.session(rs.firm_id, eng) as s:
        codes = s.execute(
            select(RecoveryCode)
            .where(RecoveryCode.user_id == rs.user_id, RecoveryCode.used_at.is_(None))
            .with_for_update()
        ).scalars()
        hit = next((c for c in codes if auth.verify_recovery_code(code, c.code_hash)), None)
        if hit is not None:
            hit.used_at = func.now()
            user = s.get(User, rs.user_id)
            assert user is not None
            extra = _enrolment(s, user)
            new = _promote(s, rs.session_id, "enrol")
            audit.record(
                s,
                firm_id=rs.firm_id,
                action="auth.recovery_code_used",
                object_type="user",
                object_id=rs.user_id,
                actor_id=rs.user_id,
            )
    if hit is None:
        _code_failed(eng, rs)
        raise DomainError(401, SIGN_IN_FAILED)
    _record(eng, [keys[1]], True)
    return Issued(new, "enrol", rs.firm_id, rs.user_id, extra)


def _issue_recovery_codes(s: Session, user: User) -> list[str]:
    s.execute(delete(RecoveryCode).where(RecoveryCode.user_id == user.id))
    codes = auth.new_recovery_codes()
    for c in codes:
        s.add(
            RecoveryCode(
                firm_id=user.firm_id, user_id=user.id, code_hash=auth.hash_recovery_code(c)
            )
        )
    return codes


def regenerate_recovery_codes(eng: Engine, *, firm_id: uuid.UUID, user_id: uuid.UUID) -> list[str]:
    with tenancy.session(firm_id, eng) as s:
        user = s.get(User, user_id)
        assert user is not None
        codes = _issue_recovery_codes(s, user)
        audit.record(
            s,
            firm_id=firm_id,
            action="auth.recovery_codes_regenerated",
            object_type="user",
            object_id=user_id,
            actor_id=user_id,
        )
        return codes


# --------------------------------------------------------------------------- password reset


def request_reset(eng: Engine, mailer: Mailer, *, email: str, client: str) -> None:
    """S-18 (a). The answer never says whether the address exists."""
    cfg = get_settings()
    email = email.strip()
    keys = [_client_key(client), _account_key("reset:" + email)]
    with tenancy.global_session(eng) as s:
        _throttle_check(s, keys)
        row = s.execute(text("SELECT * FROM pintae_login_lookup(:e)"), {"e": email}).first()
    _record(eng, [keys[0]], True)
    _record(eng, [keys[1]], False)  # every request counts towards the per-address limit
    if row is None or row.disabled:
        return
    token = auth.new_token()
    with tenancy.session(row.firm_id, eng) as s:
        s.execute(
            update(PasswordReset)
            .where(PasswordReset.user_id == row.user_id, PasswordReset.used_at.is_(None))
            .values(used_at=func.now())
        )
        s.add(
            PasswordReset(
                firm_id=row.firm_id,
                user_id=row.user_id,
                token_hash=auth.token_hash(token),
                expires_at=func.now()
                + text(f"interval '{int(cfg.password_reset_valid_minutes)} minutes'"),
            )
        )
        audit.record(
            s,
            firm_id=row.firm_id,
            action="auth.password_reset_requested",
            object_type="user",
            object_id=row.user_id,
            actor_id=None,
        )
    link = f"{cfg.public_base_url.rstrip('/')}/recover/{token}"
    mailer.send(reset_message(email, link, cfg.password_reset_valid_minutes))


def complete_reset(eng: Engine, *, token: str, password: str, client: str) -> Issued:
    """S-18 (a) completion. Ends every session of the user and returns a ``password``
    session: the TOTP code or a recovery code is still required (ASVS 6.4.3)."""
    keys = [_client_key(client)]
    with tenancy.global_session(eng) as s:
        _throttle_check(s, keys)
    _record(eng, keys, True)
    fid = _token_firm(eng, "password_reset", token)
    if fid is None:
        raise DomainError(410, "reset_invalid_or_expired")
    with tenancy.session(fid, eng) as s:
        pr = s.execute(
            select(PasswordReset)
            .where(
                PasswordReset.token_hash == auth.token_hash(token),
                PasswordReset.used_at.is_(None),
                PasswordReset.expires_at > func.now(),
            )
            .with_for_update()
        ).scalar_one_or_none()
        if pr is None:
            raise DomainError(410, "reset_invalid_or_expired")
        user = s.get(User, pr.user_id)
        assert user is not None
        if user.disabled_at is not None:
            raise DomainError(410, "reset_invalid_or_expired")
        problems = auth.password_problems(password, user.email)
        if problems:
            raise DomainError(422, "password_refused", {"problems": problems})
        pr.used_at = func.now()
        user.password_hash = auth.hash_password(password)
        _end_sessions(s, user.id)
        audit.record(
            s,
            firm_id=fid,
            action="auth.password_reset",
            object_type="user",
            object_id=user.id,
            actor_id=user.id,
        )
        stage = "password" if user.totp_confirmed_at is not None else "enrol"
        extra = _enrolment(s, user) if stage == "enrol" else {}
        return Issued(_new_session(s, user, stage), stage, fid, user.id, extra)


# --------------------------------------------------------------------------- users (S-15)


def list_users(s: Session) -> list[dict[str, Any]]:
    rows = s.execute(select(User).order_by(User.created_at)).scalars()
    return [
        {
            "id": str(u.id),
            "email": u.email,
            "role": u.role,
            "disabled": u.disabled_at is not None,
            "totp_enrolled": u.totp_confirmed_at is not None,
        }
        for u in rows
    ]


def update_user(
    eng: Engine,
    *,
    firm_id: uuid.UUID,
    actor_id: uuid.UUID,
    user_id: uuid.UUID,
    role: str | None,
    disabled: bool | None,
) -> dict[str, Any]:
    """Change role or disable. Disabling ends the user's sessions at once; the last enabled
    Owner can be neither disabled nor demoted (S-15)."""
    with tenancy.session(firm_id, eng) as s:
        s.execute(select(User.id).where(User.role == "owner").with_for_update())
        user = s.get(User, user_id)
        if user is None:
            raise DomainError(404, "not_found", {"object_type": "user", "object_id": str(user_id)})
        if role is not None and role not in ROLES:
            raise DomainError(422, "unknown_role")
        owners = s.execute(
            select(func.count())
            .select_from(User)
            .where(User.role == "owner", User.disabled_at.is_(None))
        ).scalar_one()
        removing_owner = (
            user.role == "owner"
            and user.disabled_at is None
            and (disabled is True or (role is not None and role != "owner"))
        )
        if removing_owner and owners <= 1:
            raise DomainError(409, "last_owner")
        ended = 0
        if role is not None and role != user.role:
            user.role = role
            ended += _end_sessions(s, user.id)  # role change: sign in again with the new role
        if disabled is True and user.disabled_at is None:
            user.disabled_at = func.now()
            ended += _end_sessions(s, user.id)
        elif disabled is False:
            user.disabled_at = None
        audit.record(
            s,
            firm_id=firm_id,
            action="user.updated",
            object_type="user",
            object_id=user.id,
            actor_id=actor_id,
            detail={"role": role, "disabled": disabled, "sessions_ended": ended},
        )
        s.flush()
        s.refresh(user)
        return {
            "id": str(user.id),
            "email": user.email,
            "role": user.role,
            "disabled": user.disabled_at is not None,
            "sessions_ended": ended,
        }
