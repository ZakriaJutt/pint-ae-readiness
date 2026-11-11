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

from pintae_core import audit, auth, background, tenancy
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


def _reserve(eng: Engine, client: str, account: str | None) -> uuid.UUID | None:
    """ASVS 6.3.1 (B2-S01, B2-S04): check and count in one statement, before any factor is
    verified (``pintae_auth_reserve``, migration 0008). The attempt is stored as a failure and
    becomes a success only through ``_succeeded``. Refusal is 429 with ``retry_after``."""
    cfg = get_settings()
    with tenancy.global_session(eng) as s:
        row = s.execute(
            text("SELECT * FROM pintae_auth_reserve(:c, :a, :w, :cm, :pm, :dm, :b, :cap)"),
            {
                "c": auth.throttle_key("client", client or "unknown"),
                "a": auth.throttle_key("account", account) if account is not None else None,
                "w": cfg.throttle_window_minutes,
                "cm": cfg.throttle_client_attempts,
                "pm": cfg.throttle_account_failures,
                "dm": cfg.throttle_account_clients,
                "b": cfg.throttle_delay_base_seconds,
                "cap": cfg.throttle_delay_cap_seconds,
            },
        ).one()
    if row.refused is not None:
        raise DomainError(429, "too_many_attempts", {"retry_after_seconds": int(row.retry_after)})
    aid: uuid.UUID | None = row.attempt_id
    return aid


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
    """A fresh TOTP secret held as pending (B2-001). The confirmed secret, if any, stays
    valid until a code from the pending one is confirmed in the same ``enrol`` session.

    An ``enrol`` session is created only after a fresh proof: an Owner-issued invitation
    (first enrolment or S-15 reset) or a recovery code. Never after a password or a reset
    link alone."""
    secret = auth.new_totp_secret()
    user.totp_pending_secret_enc = auth.seal_totp_secret(secret, user.id)
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
    first Owner. An open invitation of this firm to the same address is revoked."""
    cfg = get_settings()
    if role not in ROLES:
        raise DomainError(422, "unknown_role")
    email = email.strip()
    if "@" not in email or len(email) > 254:
        raise DomainError(422, "invalid_email")
    token = auth.new_token()
    with tenancy.session(firm_id, eng) as s:
        firm = s.get(Firm, firm_id)
        if firm is None:
            raise DomainError(404, "not_found", {"object_type": "firm", "object_id": str(firm_id)})
        # B2-S05: only this firm's users are visible here (row-level security). An address
        # with an account at another firm gets the invitation, and the clash is answered to
        # the invitee at acceptance, never to the inviting firm.
        if s.execute(select(User.id).where(User.email == email)).first() is not None:
            raise DomainError(409, "email_in_use")
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
    _reserve(eng, client, None)
    fid = _token_firm(eng, "invite", token)
    if fid is None:
        raise DomainError(410, "invite_invalid_or_expired")
    with tenancy.session(fid, eng) as s:
        inv = _open_invite(s, token)
        problems = auth.password_problems(password, inv.email)
        if problems:
            raise DomainError(422, "password_refused", {"problems": problems})
        if inv.user_id is not None:  # S-15 Owner reset: re-enrol the existing user
            existing = s.get(User, inv.user_id, with_for_update=True)
            if existing is None or existing.disabled_at is not None:
                raise DomainError(410, "invite_invalid_or_expired")
            user, uid = existing, existing.id
            user.password_hash = auth.hash_password(password)
            _end_sessions(s, uid)
            extra = _enrolment(s, user)
        else:
            if _user_exists(eng, inv.email):
                # Said only to the holder of the invitation, who owns the address (B2-S05).
                raise DomainError(409, "address_has_an_account")
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
    """S-01 step 1. One answer, 401 ``sign_in_failed``, for an unknown address, a wrong
    password, a disabled account and an account whose TOTP enrolment was never finished
    (B2-S05); the Owner sees "enrolment incomplete" in S-15 and re-invites."""
    email = email.strip()
    aid = _reserve(eng, client, email)
    with tenancy.global_session(eng) as s:
        row = s.execute(text("SELECT * FROM pintae_login_lookup(:e)"), {"e": email}).first()
    if row is None:
        auth.burn_password_check(password)
        raise DomainError(401, SIGN_IN_FAILED)
    ok = auth.verify_password(password, row.password_hash) and not row.disabled
    if ok:
        with tenancy.session(row.firm_id, eng) as s:
            user = s.get(User, row.user_id)
            assert user is not None
            if user.totp_confirmed_at is not None:
                issued = Issued(
                    _new_session(s, user, "password"), "password", user.firm_id, user.id
                )
                _succeeded_in(s, aid)
                return issued
    _audit_failure(eng, row.firm_id, row.user_id, "password")
    raise DomainError(401, SIGN_IN_FAILED)


def _succeeded_in(s: Session, attempt_id: uuid.UUID | None) -> None:
    if attempt_id is not None:
        s.execute(update(AuthAttempt).where(AuthAttempt.id == attempt_id).values(succeeded=True))


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


def _reserve_code(eng: Engine, rs: ResolvedSession) -> None:
    """The per-session limit, reserved in one UPDATE under the row lock before the code is
    checked (B2-S01): the sixth attempt on a session ends it."""
    cfg = get_settings()
    with tenancy.session(rs.firm_id, eng) as s:
        n = s.execute(
            text(
                "UPDATE sessions SET failed_codes = failed_codes + 1 WHERE id = :i"
                " AND ended_at IS NULL AND failed_codes < :m RETURNING failed_codes"
            ),
            {"i": rs.session_id, "m": cfg.totp_failures_per_session},
        ).scalar_one_or_none()
        if n is None:
            s.execute(
                update(SessionRow).where(SessionRow.id == rs.session_id).values(ended_at=func.now())
            )
    if n is None:
        raise DomainError(401, "sign_in_required")


def _code_failed(eng: Engine, rs: ResolvedSession) -> None:
    _audit_failure(eng, rs.firm_id, rs.user_id, "code")


def complete_totp(
    eng: Engine, *, token: str | None, code: str, client: str, now: datetime
) -> Issued:
    """S-01 step 2 (``password`` session) or S-02 step 2 (``enrol`` session). Enrolment
    issues ten recovery codes, shown once."""
    rs = _pending(eng, token, ("password", "enrol"))
    aid = _reserve(eng, client, f"user:{rs.user_id}")
    _reserve_code(eng, rs)
    with tenancy.session(rs.firm_id, eng) as s:
        user = s.get(User, rs.user_id, with_for_update=True)
        assert user is not None
        if rs.stage == "enrol":  # the pending secret, never the confirmed one
            sealed, last = user.totp_pending_secret_enc, None
        else:  # a full session only with a confirmed factor
            sealed = user.totp_secret_enc if user.totp_confirmed_at is not None else None
            last = user.totp_last_step
        secret = auth.open_totp_secret(sealed, user.id) if sealed else None
        step = auth.verify_totp(secret, code, now, last) if secret else None
        if step is None:
            ok = False
        else:
            ok = True
            user.totp_last_step = step
            extra: dict[str, Any] = {}
            if rs.stage == "enrol":
                user.totp_secret_enc = user.totp_pending_secret_enc or b""
                user.totp_pending_secret_enc = None
                user.totp_confirmed_at = func.now()
                extra["recovery_codes"] = _issue_recovery_codes(s, user)
                s.execute(  # sessions started under the old factor end
                    update(SessionRow)
                    .where(
                        SessionRow.user_id == user.id,
                        SessionRow.id != rs.session_id,
                        SessionRow.ended_at.is_(None),
                    )
                    .values(ended_at=func.now())
                )
            new = _promote(s, rs.session_id, "full")
            _succeeded_in(s, aid)
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
    return Issued(new, "full", rs.firm_id, rs.user_id, extra)


def recovery_step(eng: Engine, *, token: str | None, code: str, client: str) -> Issued:
    """S-18 (b): a single-use recovery code instead of the TOTP code, then forced
    re-enrolment: the session moves to ``enrol`` with a new pending TOTP secret. Its only
    permitted action is confirming that secret. The old TOTP and the other recovery codes
    stay valid until then (B2-001)."""
    rs = _pending(eng, token, ("password",))
    aid = _reserve(eng, client, f"user:{rs.user_id}")
    _reserve_code(eng, rs)
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
            _succeeded_in(s, aid)
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
    """S-18 (a). The same status, body and timing whether or not the address has an
    account (B2-S03): the request only reserves a throttle slot and queues the work; the
    lookup, the reset row, the audit event and the mail happen after the response. The
    per-(address, client) limit and the capped account delay (B2-S04) apply; at most
    ``reset_mails_per_window`` mails go to one address per window, so others are dropped."""
    email = email.strip()
    _reserve(eng, client, "reset:" + email)
    background.submit(lambda: _send_reset(eng, mailer, email))


def _send_reset(eng: Engine, mailer: Mailer, email: str) -> None:
    cfg = get_settings()
    with tenancy.global_session(eng) as s:
        row = s.execute(text("SELECT * FROM pintae_login_lookup(:e)"), {"e": email}).first()
    if row is None or row.disabled:
        return
    token = auth.new_token()
    with tenancy.session(row.firm_id, eng) as s:
        user = s.get(User, row.user_id)
        if user is None or user.totp_confirmed_at is None:
            return  # an unenrolled account is re-invited by its Owner (B2-001)
        recent = s.execute(
            select(func.count())
            .select_from(PasswordReset)
            .where(
                PasswordReset.user_id == row.user_id,
                PasswordReset.created_at
                > func.now() - text(f"interval '{int(cfg.throttle_window_minutes)} minutes'"),
            )
        ).scalar_one()
        if recent >= cfg.reset_mails_per_window:
            return
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
    _reserve(eng, client, None)
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
        if user.totp_confirmed_at is None:
            # B2-001: a reset link alone never starts an enrolment; the Owner re-invites.
            raise DomainError(403, "totp_enrolment_required")
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
        return Issued(_new_session(s, user, "password"), "password", fid, user.id)


# --------------------------------------------------------------------------- users (S-15)


def reset_user(
    eng: Engine, mailer: Mailer, *, firm_id: uuid.UUID, actor_id: uuid.UUID, user_id: uuid.UUID
) -> uuid.UUID:
    """S-15 "Reset sign-in" (TRD 8.1 (c)): the Owner ends the user's sessions, makes the
    password unusable and e-mails a new invitation to the same address. Accepting it sets a
    new password and requires TOTP enrolment in that same flow. An Owner cannot reset
    themself (that is the vendor path, 8.1 (d))."""
    cfg = get_settings()
    if user_id == actor_id:
        raise DomainError(409, "cannot_reset_self")
    token = auth.new_token()
    with tenancy.session(firm_id, eng) as s:
        user = s.get(User, user_id, with_for_update=True)
        if user is None:
            raise DomainError(404, "not_found", {"object_type": "user", "object_id": str(user_id)})
        if user.disabled_at is not None:
            raise DomainError(409, "user_disabled")
        firm = s.get(Firm, firm_id)
        assert firm is not None
        ended = _end_sessions(s, user.id)
        user.password_hash = "!reset"  # noqa: S105 - unusable marker: no password verifies
        user.totp_pending_secret_enc = None
        s.execute(
            update(Invite)
            .where(
                Invite.email == user.email, Invite.used_at.is_(None), Invite.revoked_at.is_(None)
            )
            .values(revoked_at=func.now())
        )
        inv = Invite(
            firm_id=firm_id,
            created_by=actor_id,
            email=user.email,
            role=user.role,
            user_id=user.id,
            token_hash=auth.token_hash(token),
            expires_at=func.now() + text(f"interval '{int(cfg.invite_valid_hours)} hours'"),
        )
        s.add(inv)
        s.flush()
        audit.record(
            s,
            firm_id=firm_id,
            action="user.sign_in_reset",
            object_type="user",
            object_id=user.id,
            actor_id=actor_id,
            detail={"sessions_ended": ended},
        )
        email, role, firm_name, invite_id = user.email, user.role, firm.legal_name, inv.id
    link = f"{cfg.public_base_url.rstrip('/')}/invite/{token}"
    mailer.send(invite_message(email, firm_name, role, link, cfg.invite_valid_hours))
    return invite_id


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
