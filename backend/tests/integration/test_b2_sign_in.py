"""B2 sign-in end to end through the API, with e-mail read from the local Mailpit inbox:
invitation, password plus TOTP enrolment, sign-in, anti-forgery, sign-out, expiry and
revocation, cross-firm refusal, the throttle, password reset and recovery codes."""

from __future__ import annotations

import base64
import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from sqlalchemy import text

from pintae_api.deps import SESSION_COOKIE
from pintae_core import auth
from tests.integration import flow, mailpit
from tests.integration.conftest import Env, Firm

PASSWORD = "plover-candle-harbour-9"
pytestmark = pytest.mark.usefixtures("_mailpit")


@pytest.fixture
def _mailpit() -> None:
    mailpit.require()


@pytest.fixture
def addresses() -> Iterator[list[str]]:
    used: list[str] = []
    yield used
    for a in used:
        mailpit.delete_to(a)


def _addr(used: list[str], label: str) -> str:
    a = f"{label}.{uuid.uuid4().hex[:10]}@firm.test"
    used.append(a)
    return a


def _cookie(resp: Any) -> str:
    raw = resp.headers.get("set-cookie", "")
    assert raw.startswith(f"{SESSION_COOKIE}="), raw
    return str(raw.split(";", 1)[0].split("=", 1)[1])


def _h(token: str, csrf: str | None = None) -> dict[str, str]:
    h = {"Cookie": f"{SESSION_COOKIE}={token}"}
    if csrf:
        h["X-CSRF-Token"] = csrf
    return h


def _code(env: Env, secret_b32: str, offset_steps: int = 0) -> str:
    secret = base64.b32decode(secret_b32 + "=" * (-len(secret_b32) % 8))
    return auth.totp_code(secret, auth.totp_step(env.clock[0]) + offset_steps)


class Member:
    """A user who joined through the real invitation flow."""

    def __init__(self, email: str, secret: str, token: str, csrf: str, codes: list[str]) -> None:
        self.email, self.secret, self.token, self.csrf, self.codes = (
            email,
            secret,
            token,
            csrf,
            codes,
        )

    def h(self) -> dict[str, str]:
        return _h(self.token, self.csrf)


def _invite(env: Env, firm: Firm, email: str, role: str = "reviewer") -> str:
    r = env.client.post("/api/v1/invites", headers=firm.h(), json={"email": email, "role": role})
    assert r.status_code == 201, r.text
    return mailpit.link_token(mailpit.latest_text(email), "invite")


def _join(env: Env, firm: Firm, email: str, role: str = "reviewer") -> Member:
    c = env.client
    c.cookies.clear()
    tok = _invite(env, firm, email, role)
    r = c.post(f"/api/v1/invites/{tok}/accept", json={"password": PASSWORD})
    assert r.status_code == 200 and r.json()["stage"] == "enrol", r.text
    secret, pending = r.json()["totp_secret"], _cookie(r)
    r = c.post("/api/v1/auth/totp", headers=_h(pending), json={"code": _code(env, secret)})
    assert r.status_code == 200, r.text
    body = r.json()
    return Member(email, secret, _cookie(r), body["csrf_token"], body["recovery_codes"])


def _login(env: Env, email: str, password: str = PASSWORD) -> Any:
    env.client.cookies.clear()
    return env.client.post("/api/v1/auth/login", json={"email": email, "password": password})


# --------------------------------------------------------------------------- invitation, sign-in


def test_invite_enrol_sign_in_sign_out_end_to_end(env: Env, addresses: list[str]) -> None:
    c = env.client
    firm = env.firm()
    email = _addr(addresses, "reviewer")
    tok = _invite(env, firm, email)
    body = mailpit.latest_text(email)
    assert "expires in 24 hours" in body and "/invite/" in body
    info = c.get(f"/api/v1/invites/{tok}").json()
    assert info == {"firm": "Synthetic Bookkeeping FZ-LLC", "role": "reviewer", "email": email}
    # A weak or breached password is refused with a reason; the invitation stays usable.
    r = c.post(f"/api/v1/invites/{tok}/accept", json={"password": "short"})
    assert r.status_code == 422 and r.json()["problems"] == ["too_short"]
    r = c.post(f"/api/v1/invites/{tok}/accept", json={"password": "Password1234"})
    assert r.status_code == 422 and "breached_password" in r.json()["problems"]
    r = c.post(f"/api/v1/invites/{tok}/accept", json={"password": PASSWORD})
    assert r.status_code == 200 and r.json()["stage"] == "enrol"
    assert r.json()["otpauth_uri"].startswith("otpauth://totp/")
    secret, pending = r.json()["totp_secret"], _cookie(r)
    # The invitation works once.
    assert c.post(f"/api/v1/invites/{tok}/accept", json={"password": PASSWORD}).status_code == 410
    # A session in the enrolment stage reaches no application route.
    c.cookies.clear()
    assert c.get("/api/v1/dashboard", headers=_h(pending)).status_code == 401
    assert (
        c.post("/api/v1/auth/totp", headers=_h(pending), json={"code": "000000"}).status_code == 401
    )
    r = c.post("/api/v1/auth/totp", headers=_h(pending), json={"code": _code(env, secret)})
    assert r.status_code == 200 and r.json()["stage"] == "full"
    assert len(r.json()["recovery_codes"]) == 10
    full, csrf = _cookie(r), r.json()["csrf_token"]
    assert full != pending  # a new token once signed in (ASVS 7.2.4)
    c.cookies.clear()
    assert c.get("/api/v1/dashboard", headers=_h(pending)).status_code == 401
    assert c.get("/api/v1/dashboard", headers=_h(full)).status_code == 200
    me = c.get("/api/v1/auth/session", headers=_h(full)).json()
    assert me["role"] == "reviewer" and me["firm_id"] == str(firm.id) and me["csrf_token"] == csrf
    # Anti-forgery: a state-changing request needs the token tied to this session.
    new = {"legal_name": "Synthetic Client LLC"}
    assert c.post("/api/v1/entities", headers=_h(full), json=new).status_code == 403
    assert c.post("/api/v1/entities", headers=_h(full, "x" * 64), json=new).status_code == 403
    assert c.post("/api/v1/entities", headers=_h(full, csrf), json=new).status_code == 201
    # Sign-out ends the session at once.
    assert c.post("/api/v1/auth/logout", headers=_h(full)).status_code == 403
    r = c.post("/api/v1/auth/logout", headers=_h(full, csrf))
    assert r.status_code == 204
    assert c.get("/api/v1/dashboard", headers=_h(full)).status_code == 401
    # Sign in again: password, then a TOTP code that has not been used before.
    r = _login(env, email)
    assert r.status_code == 200 and r.json() == {"stage": "password"}
    pw = _cookie(r)
    c.cookies.clear()
    replay = c.post("/api/v1/auth/totp", headers=_h(pw), json={"code": _code(env, secret)})
    assert replay.status_code == 401  # the enrolment code is not accepted twice
    r = c.post("/api/v1/auth/totp", headers=_h(pw), json={"code": _code(env, secret, 1)})
    assert r.status_code == 200 and r.json()["stage"] == "full"
    with env.admin.connect() as conn:
        actions = (
            conn.execute(
                text("SELECT action FROM audit_events WHERE firm_id = :f ORDER BY created_at"),
                {"f": firm.id},
            )
            .scalars()
            .all()
        )
    for a in ("user.invited", "user.invite_accepted", "auth.totp_enrolled", "auth.signed_out",
              "auth.signed_in", "auth.sign_in_failed"):  # fmt: skip
        assert a in actions, (a, actions)


def test_session_cookie_attributes(env: Env, addresses: list[str]) -> None:
    firm = env.firm()
    email = _addr(addresses, "cookie")
    tok = _invite(env, firm, email)
    r = env.client.post(f"/api/v1/invites/{tok}/accept", json={"password": PASSWORD})
    attrs = [a.strip().lower() for a in r.headers["set-cookie"].split(";")]
    assert attrs[0].startswith("__host-pintae_session=")
    assert {"secure", "httponly", "samesite=lax", "path=/"} <= set(attrs)
    assert not any(a.startswith(("domain=", "expires=", "max-age=")) for a in attrs)
    assert r.headers["cache-control"] == "no-store"


def test_expired_and_revoked_invitations_are_refused(env: Env, addresses: list[str]) -> None:
    firm = env.firm()
    email = _addr(addresses, "late")
    old = _invite(env, firm, email)
    with env.admin.begin() as conn:
        conn.execute(
            text("UPDATE invites SET expires_at = now() - interval '1 minute' WHERE email = :e"),
            {"e": email},
        )
    r = env.client.post(f"/api/v1/invites/{old}/accept", json={"password": PASSWORD})
    assert r.status_code == 410 and r.json()["reason"] == "invite_invalid_or_expired"
    first = _invite(env, firm, _addr(addresses, "twice"))
    _invite(env, firm, addresses[-1])  # a second invitation revokes the first
    assert (
        env.client.post(f"/api/v1/invites/{first}/accept", json={"password": PASSWORD}).status_code
        == 410
    )
    assert env.client.get("/api/v1/invites/not-a-token").status_code == 410


def test_only_an_owner_invites_and_an_existing_address_is_refused(
    env: Env, addresses: list[str]
) -> None:
    firm = env.firm()
    email = _addr(addresses, "dup")
    r = env.client.post(
        "/api/v1/invites", headers=firm.h("reviewer"), json={"email": email, "role": "preparer"}
    )
    assert r.status_code == 403
    _join(env, firm, email)
    r = env.client.post("/api/v1/invites", headers=firm.h(), json={"email": email, "role": "owner"})
    assert r.status_code == 409 and r.json()["reason"] == "email_in_use"


# --------------------------------------------------------------------------- expiry, revocation


def test_expiry_disable_and_role_change_end_sessions(env: Env, addresses: list[str]) -> None:
    c = env.client
    firm = env.firm()
    m = _join(env, firm, _addr(addresses, "member"))
    assert c.get("/api/v1/dashboard", headers=m.h()).status_code == 200
    with env.admin.begin() as conn:
        conn.execute(
            text("UPDATE sessions SET absolute_expires_at = now() - interval '1 second' "
                 "WHERE token_hash = :h"),
            {"h": auth.token_hash(m.token)},
        )  # fmt: skip
    assert c.get("/api/v1/dashboard", headers=m.h()).status_code == 401
    r = _login(env, m.email)
    pw = _cookie(r)
    c.cookies.clear()
    r = c.post("/api/v1/auth/totp", headers=_h(pw), json={"code": _code(env, m.secret, 1)})
    tok2, csrf2 = _cookie(r), r.json()["csrf_token"]
    uid = c.get("/api/v1/auth/session", headers=_h(tok2)).json()["user_id"]
    users = c.get("/api/v1/users", headers=firm.h()).json()["items"]
    assert {u["email"] for u in users} >= {m.email}
    assert c.get("/api/v1/users", headers=_h(tok2)).status_code == 403  # reviewer
    r = c.patch(f"/api/v1/users/{uid}", headers=firm.h(), json={"role": "preparer"})
    assert r.status_code == 200 and r.json()["sessions_ended"] >= 1
    assert c.get("/api/v1/dashboard", headers=_h(tok2, csrf2)).status_code == 401
    r = c.patch(f"/api/v1/users/{uid}", headers=firm.h(), json={"disabled": True})
    assert r.status_code == 200 and r.json()["disabled"] is True
    assert _login(env, m.email).status_code == 401  # a disabled user cannot sign in
    # The last enabled Owner can be neither disabled nor demoted.
    owner = str(firm.users["owner"])
    r = c.patch(f"/api/v1/users/{owner}", headers=firm.h(), json={"disabled": True})
    assert r.status_code == 409 and r.json()["reason"] == "last_owner"
    r = c.patch(f"/api/v1/users/{owner}", headers=firm.h(), json={"role": "reviewer"})
    assert r.status_code == 409


def test_session_of_one_firm_never_reaches_another(env: Env, addresses: list[str]) -> None:
    a, b = env.firm("Firm A"), env.firm("Firm B")
    eid = flow.new_entity(env, a, "A Client LLC")
    mb = _join(env, b, _addr(addresses, "firm-b"))
    c = env.client
    assert c.get(f"/api/v1/entities/{eid}", headers=mb.h()).status_code == 404
    assert c.patch(f"/api/v1/entities/{eid}", headers=mb.h(), json={"city": "X"}).status_code == 404
    users_a = c.get("/api/v1/users", headers=a.h()).json()["items"]
    assert mb.email not in {u["email"] for u in users_a}
    # Firm B's anti-forgery token does not work with firm A's session, nor the reverse.
    r = c.post(
        "/api/v1/entities",
        headers=_h(a.tokens["owner"], mb.csrf),
        json={"legal_name": "Synthetic Client LLC"},
    )
    assert r.status_code == 403


def test_cross_origin_state_change_is_refused(env: Env) -> None:
    firm = env.firm()
    r = env.client.post(
        "/api/v1/entities",
        headers=firm.h(Origin="https://evil.example"),
        json={"legal_name": "Synthetic Client LLC"},
    )
    assert r.status_code == 403 and r.json()["reason"] == "cross_origin_refused"


# --------------------------------------------------------------------------- throttle


def test_account_throttle_after_five_failures(env: Env, addresses: list[str]) -> None:
    firm = env.firm()
    m = _join(env, firm, _addr(addresses, "throttle"))
    for _ in range(5):
        r = _login(env, m.email, "wrong-password-123")
        assert r.status_code == 401 and r.json() == {"reason": "sign_in_failed"}
    r = _login(env, m.email)  # the right password is not even checked now
    assert r.status_code == 429 and r.json()["reason"] == "too_many_attempts"
    # Another account from the same client is not locked out by this one.
    other = _login(env, "nobody." + uuid.uuid4().hex[:8] + "@firm.test")
    assert other.status_code == 401
    # The window passes (simulated by ageing the attempts), then sign-in works again.
    with env.admin.begin() as conn:
        conn.execute(text("UPDATE auth_attempts SET at = at - interval '16 minutes'"))
    assert _login(env, m.email).status_code == 200


def test_unknown_address_and_wrong_password_look_the_same(env: Env, addresses: list[str]) -> None:
    firm = env.firm()
    m = _join(env, firm, _addr(addresses, "same"))
    a = _login(env, m.email, "wrong-password-123")
    b = _login(env, "absent." + uuid.uuid4().hex[:8] + "@firm.test", "wrong-password-123")
    assert (
        (a.status_code, a.json())
        == (b.status_code, b.json())
        == (401, {"reason": "sign_in_failed"})
    )


def test_client_throttle(env: Env) -> None:
    statuses = [
        _login(env, f"probe{i}.{uuid.uuid4().hex[:6]}@firm.test", "wrong-password-123").status_code
        for i in range(31)
    ]
    assert statuses[:30] == [401] * 30 and statuses[30] == 429


def test_code_guessing_ends_the_pending_session(env: Env, addresses: list[str]) -> None:
    firm = env.firm()
    m = _join(env, firm, _addr(addresses, "guess"))
    pw = _cookie(_login(env, m.email))
    c = env.client
    c.cookies.clear()
    for _ in range(5):
        assert c.post("/api/v1/auth/totp", headers=_h(pw), json={"code": "000000"}).status_code in (
            401,
            429,
        )
    r = c.post("/api/v1/auth/totp", headers=_h(pw), json={"code": _code(env, m.secret, 1)})
    assert r.status_code in (401, 429)  # the session ended after five wrong codes


# --------------------------------------------------------------------------- recovery


def test_password_reset_by_mailed_link_still_needs_totp(env: Env, addresses: list[str]) -> None:
    c = env.client
    firm = env.firm()
    m = _join(env, firm, _addr(addresses, "reset"))
    r = c.post("/api/v1/auth/password-reset", json={"email": m.email})
    assert r.status_code == 202
    body = mailpit.latest_text(m.email, count=2)
    assert "expires in 20 minutes" in body
    tok = mailpit.link_token(body, "recover")
    # The answer is the same for an address with no account, and no mail is sent.
    ghost = _addr(addresses, "ghost")
    assert c.post("/api/v1/auth/password-reset", json={"email": ghost}).status_code == 202
    assert mailpit.messages_to(ghost) == []
    new_pw = "lantern-meadow-quartz-4"
    r = c.post(f"/api/v1/auth/password-reset/{tok}", json={"password": new_pw})
    assert r.status_code == 200 and r.json() == {"stage": "password"}  # TOTP still required
    pending = _cookie(r)
    assert c.get("/api/v1/dashboard", headers=m.h()).status_code == 401  # old session ended
    c.cookies.clear()
    assert c.get("/api/v1/dashboard", headers=_h(pending)).status_code == 401
    r = c.post("/api/v1/auth/totp", headers=_h(pending), json={"code": _code(env, m.secret, 1)})
    assert r.status_code == 200 and r.json()["stage"] == "full"
    # The link works once; the old password no longer works; the new one does.
    r = c.post(f"/api/v1/auth/password-reset/{tok}", json={"password": new_pw})
    assert r.status_code == 410
    assert _login(env, m.email).status_code == 401
    assert _login(env, m.email, new_pw).status_code == 200


def test_expired_reset_link_is_refused(env: Env, addresses: list[str]) -> None:
    firm = env.firm()
    m = _join(env, firm, _addr(addresses, "stale"))
    env.client.post("/api/v1/auth/password-reset", json={"email": m.email})
    tok = mailpit.link_token(mailpit.latest_text(m.email, count=2), "recover")
    with env.admin.begin() as conn:
        conn.execute(text("UPDATE password_resets SET expires_at = now() - interval '1 second'"))
    r = env.client.post(
        f"/api/v1/auth/password-reset/{tok}", json={"password": "another-long-pass-7"}
    )
    assert r.status_code == 410


def test_recovery_code_signs_in_once_and_forces_reenrolment(env: Env, addresses: list[str]) -> None:
    c = env.client
    firm = env.firm()
    m = _join(env, firm, _addr(addresses, "lost"))
    pw = _cookie(_login(env, m.email))
    c.cookies.clear()
    r = c.post("/api/v1/auth/recovery-code", headers=_h(pw), json={"code": m.codes[0]})
    assert r.status_code == 200 and r.json()["stage"] == "enrol"
    new_secret, enrol = r.json()["totp_secret"], _cookie(r)
    assert new_secret != m.secret
    c.cookies.clear()
    assert c.get("/api/v1/dashboard", headers=_h(enrol)).status_code == 401
    r = c.post("/api/v1/auth/totp", headers=_h(enrol), json={"code": _code(env, new_secret)})
    assert r.status_code == 200 and len(r.json()["recovery_codes"]) == 10
    # The old secret and the old recovery codes are gone.
    pw = _cookie(_login(env, m.email))
    c.cookies.clear()
    r = c.post("/api/v1/auth/totp", headers=_h(pw), json={"code": _code(env, m.secret, 1)})
    assert r.status_code == 401
    pw = _cookie(_login(env, m.email))
    c.cookies.clear()
    r = c.post("/api/v1/auth/recovery-code", headers=_h(pw), json={"code": m.codes[0]})
    assert r.status_code == 401  # a used code is refused the second time (IT-18)
    r = c.post("/api/v1/auth/recovery-code", headers=_h(pw), json={"code": m.codes[1]})
    assert r.status_code == 401  # the old set was replaced at re-enrolment


def test_pending_session_expires(env: Env, addresses: list[str]) -> None:
    firm = env.firm()
    m = _join(env, firm, _addr(addresses, "slow"))
    pw = _cookie(_login(env, m.email))
    with env.admin.begin() as conn:
        conn.execute(
            text("UPDATE sessions SET absolute_expires_at = now() - interval '1 second' "
                 "WHERE token_hash = :h"),
            {"h": auth.token_hash(pw)},
        )  # fmt: skip
    env.client.cookies.clear()
    r = env.client.post("/api/v1/auth/totp", headers=_h(pw), json={"code": _code(env, m.secret, 1)})
    assert r.status_code == 401
