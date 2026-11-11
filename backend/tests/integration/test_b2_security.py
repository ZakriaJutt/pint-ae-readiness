"""Regressions for the independent B2 security review, round 1 (B2-S01 to B2-S06).

B2-S01 throttle reserved atomically (40 parallel requests against a real uvicorn server);
B2-S02 tests that fail if HSTS/CSP, recovery-code hashing or the per-session code limit are
removed; B2-S03 identical reset answers and timing; B2-S04 no lock-out of a victim by a third
party; B2-S05 no account oracle by message or across firms; B2-S06 CSV quoting and formula
neutralising for comma and semicolon readers.
"""

from __future__ import annotations

import csv
import io
import os
import socket
import statistics
import subprocess
import sys
import time
import uuid
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from pintae_api.deps import SESSION_COOKIE
from pintae_core import auth, background
from pintae_core.config import get_settings
from pintae_core.exports import csv_bytes, safe_cell
from tests.integration import mailpit
from tests.integration.conftest import Env, Firm
from tests.integration.test_b2_sign_in import PASSWORD, _addr, _code, _cookie, _h, _join, _login

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def _mail() -> None:
    mailpit.require()


@pytest.fixture
def addresses() -> Iterator[list[str]]:
    used: list[str] = []
    yield used
    background.wait_idle()
    for a in used:
        mailpit.delete_to(a)


def _peer(env: Env, ip: str) -> TestClient:
    """The same application seen from another client address."""
    return TestClient(env.client.app, base_url="https://testserver", client=(ip, 40000))


def _seed(env: Env, firm: Firm, *, enrolled: bool = True) -> tuple[str, bytes, uuid.UUID]:
    uid = uuid.uuid4()
    email = f"seed.{uid.hex[:10]}@firm.test"
    secret = auth.new_totp_secret()
    with env.admin.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO users (id, firm_id, email, role, password_hash, totp_secret_enc,"
                " totp_confirmed_at) VALUES (:i, :f, :e, 'reviewer', :p, :t,"
                " CASE WHEN :en THEN now() END)"
            ),
            {"i": uid, "f": firm.id, "e": email, "p": auth.hash_password(PASSWORD),
             "t": auth.seal_totp_secret(secret, uid), "en": enrolled},
        )  # fmt: skip
    return email, secret, uid


# --------------------------------------------------------------------------- B2-S01


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port: int = s.getsockname()[1]
        return port


@pytest.fixture
def server(env: Env, tmp_path: Path) -> Iterator[str]:
    """uvicorn, one process as `make dev` runs it, against pintae_test on a free port."""
    port = _free_port()
    e = dict(os.environ)
    e.update(
        PINTAE_ENV="test",
        PINTAE_STORAGE_BACKEND="local",
        PINTAE_STORAGE_ROOT=str(tmp_path / "storage"),
        PYTHONPATH=os.pathsep.join(
            str(ROOT / p)
            for p in (
                "apps/api",
                "apps/worker",
                "packages/core",
                "packages/rules",
                "packages/rulepacks",
                "packages/ingest",
            )
        ),
    )
    log = (tmp_path / "uvicorn.log").open("w")
    p = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "pintae_api.main:create_app", "--factory",
         "--host", "127.0.0.1", "--port", str(port), "--no-access-log"],
        env=e, cwd=ROOT, stdout=log, stderr=log,
    )  # fmt: skip
    try:
        for _ in range(150):
            try:
                if httpx.get(f"http://127.0.0.1:{port}/healthz", timeout=1).status_code == 200:
                    break
            except httpx.HTTPError:
                time.sleep(0.1)
        else:
            raise RuntimeError("server did not start")
        yield f"http://127.0.0.1:{port}/api/v1"
    finally:
        p.terminate()
        p.wait(timeout=10)
        log.close()


def _reasons(res: list[httpx.Response]) -> list[str]:
    return [f"{r.status_code}:{r.json().get('reason')}" for r in res]


def test_b2_s01_forty_parallel_requests_on_a_real_server_stay_within_the_limits(
    env: Env, server: str
) -> None:
    firm = env.firm()
    email, _, _ = _seed(env, firm)
    hc = httpx.Client(timeout=60)

    def login(pw: str = PASSWORD) -> httpx.Response:
        return hc.post(f"{server}/auth/login", json={"email": email, "password": pw})

    def tok(r: httpx.Response) -> str:
        return str(r.headers["set-cookie"].split(";", 1)[0].split("=", 1)[1])

    def clear() -> None:
        with env.admin.begin() as conn:
            conn.execute(text("DELETE FROM auth_attempts"))

    def totp(token: str, i: int) -> httpx.Response:
        return hc.post(
            f"{server}/auth/totp",
            headers={"Cookie": f"{SESSION_COOKIE}={token}"},
            json={"code": f"{(i * 7919) % 1000000:06d}"},
        )

    # Password: 40 wrong passwords at once for one address.
    with ThreadPoolExecutor(40) as ex:
        res = list(ex.map(lambda i: login(f"wrong-password-{i:04d}"), range(40)))
    assert _reasons(res).count("401:sign_in_failed") <= 5, _reasons(res)
    clear()
    # TOTP: 40 wrong codes at once on one pending session.
    pw = tok(login())
    with ThreadPoolExecutor(40) as ex:
        res = list(ex.map(lambda i: totp(pw, i), range(40)))
    evaluated = _reasons(res).count("401:sign_in_failed")
    with env.admin.connect() as conn:
        failed_codes = conn.execute(
            text("SELECT failed_codes FROM sessions WHERE token_hash = :h"),
            {"h": auth.token_hash(pw)},
        ).scalar_one()
    assert evaluated <= 5, _reasons(res)
    assert failed_codes == evaluated  # no lost increments
    clear()
    # TOTP: 40 wrong codes at once over 8 pending sessions.
    toks = [tok(login()) for _ in range(8)]
    with ThreadPoolExecutor(40) as ex:
        res = list(ex.map(lambda i: totp(toks[i % 8], i), range(40)))
    assert _reasons(res).count("401:sign_in_failed") <= 5, _reasons(res)


# --------------------------------------------------------------------------- B2-S02


def test_b2_s02_security_headers_on_every_kind_of_response(env: Env) -> None:
    firm = env.firm()
    c = env.client
    for r in (
        c.get("/api/v1/dashboard", headers=firm.h()),
        c.get("/api/v1/dashboard"),
        c.post("/api/v1/entities", headers=firm.h(Origin="https://evil.example"), json={}),
        c.get(f"/api/v1/files/{uuid.uuid4()}", headers=firm.h()),
        c.post("/api/v1/auth/login", json={}),
    ):
        assert r.headers["strict-transport-security"].startswith("max-age=")
        csp = r.headers["content-security-policy"]
        assert "object-src 'none'" in csp and "base-uri 'none'" in csp
        assert r.headers["x-content-type-options"] == "nosniff"


def test_b2_s02_recovery_codes_are_stored_as_salted_hashes(env: Env, _mail: None) -> None:
    firm = env.firm()
    m = _join(env, firm, f"codes.{uuid.uuid4().hex[:10]}@firm.test")
    with env.admin.connect() as conn:
        stored = (
            conn.execute(
                text(
                    "SELECT code_hash FROM recovery_codes WHERE user_id ="
                    " (SELECT id FROM users WHERE email = :e)"
                ),
                {"e": m.email},
            )
            .scalars()
            .all()
        )
    assert len(stored) == 10 and len(set(stored)) == 10
    assert all(h.startswith("scrypt$") for h in stored)
    blob = " ".join(stored).upper()
    for code in m.codes:
        assert code not in blob and auth.normalise_recovery_code(code) not in blob
    mailpit.delete_to(m.email)


def test_b2_s02_sixth_code_on_one_session_is_refused_by_the_session_rule(
    env: Env, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The per-session limit alone, with the account and client limits out of the way."""
    cfg = get_settings()
    monkeypatch.setattr(cfg, "throttle_account_failures", 1000)
    monkeypatch.setattr(cfg, "throttle_account_clients", 1000)
    monkeypatch.setattr(cfg, "throttle_client_attempts", 1000)
    firm = env.firm()
    email, secret, _ = _seed(env, firm)
    pw = _cookie(_login(env, email))
    c = env.client
    c.cookies.clear()
    for _ in range(5):
        r = c.post("/api/v1/auth/totp", headers=_h(pw), json={"code": "000000"})
        assert r.json() == {"reason": "sign_in_failed"}
    right = auth.totp_code(secret, auth.totp_step(env.clock[0]))
    r = c.post("/api/v1/auth/totp", headers=_h(pw), json={"code": right})
    assert (r.status_code, r.json()) == (401, {"reason": "sign_in_required"})
    with env.admin.connect() as conn:
        ended = conn.execute(
            text("SELECT ended_at IS NOT NULL FROM sessions WHERE token_hash = :h"),
            {"h": auth.token_hash(pw)},
        ).scalar_one()
    assert ended


# --------------------------------------------------------------------------- B2-S03


def test_b2_s03_reset_request_answers_the_same_for_known_and_unknown(
    env: Env, _mail: None, addresses: list[str]
) -> None:
    firm = env.firm()
    m = _join(env, firm, _addr(addresses, "known"))
    absent = _addr(addresses, "absent")
    c = env.client

    def timed(email: str) -> tuple[float, Any]:
        with env.admin.begin() as conn:
            conn.execute(text("DELETE FROM auth_attempts"))
        t = time.perf_counter()
        r = c.post("/api/v1/auth/password-reset", json={"email": email})
        return (time.perf_counter() - t) * 1000, r

    known, unknown = [], []
    for _ in range(15):
        tk, rk = timed(m.email)
        tu, ru = timed(absent)
        assert (
            (rk.status_code, rk.json())
            == (ru.status_code, ru.json())
            == (
                202,
                {"status": "if_the_address_has_an_account_a_link_was_sent"},
            )
        )
        known.append(tk)
        unknown.append(tu)
    mk, mu = statistics.median(known), statistics.median(unknown)
    assert mk < 1.5 * mu + 2.0, (mk, mu)  # no per-request lookup, row or SMTP send
    background.wait_idle()
    assert mailpit.messages_to(absent) == []


# --------------------------------------------------------------------------- B2-S04


def test_b2_s04_third_party_cannot_lock_out_a_victim(
    env: Env, _mail: None, addresses: list[str]
) -> None:
    firm = env.firm()
    email, _, _ = _seed(env, firm)
    addresses.append(email)
    attacker, victim = _peer(env, "203.0.113.7"), _peer(env, "198.51.100.20")
    for i in range(5):
        attacker.post("/api/v1/auth/login", json={"email": email, "password": f"nope-{i:04d}xx"})
    r = attacker.post("/api/v1/auth/login", json={"email": email, "password": "nope-9999xx"})
    assert r.status_code == 429  # the attacker's address is limited
    assert (
        victim.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD}).status_code
        == 200
    )
    for _ in range(6):
        attacker.post("/api/v1/auth/password-reset", json={"email": email})
    assert victim.post("/api/v1/auth/password-reset", json={"email": email}).status_code == 202
    background.wait_idle()
    # The victim's mailbox is not flooded: at most the per-window cap of reset mails.
    assert len(mailpit.messages_to(email)) <= get_settings().reset_mails_per_window


def test_b2_s04_many_addresses_get_a_capped_delay_not_a_lock(env: Env) -> None:
    firm = env.firm()
    email, _, _ = _seed(env, firm)
    for i in range(5):
        r = _peer(env, f"10.5.0.{i}").post(
            "/api/v1/auth/login", json={"email": email, "password": f"wrong-{i:04d}xxxx"}
        )
        assert r.status_code == 401
    r = _peer(env, "10.5.0.99").post(
        "/api/v1/auth/login", json={"email": email, "password": PASSWORD}
    )
    assert r.status_code == 429
    cap = get_settings().throttle_delay_cap_seconds
    assert 0 < r.json()["retry_after_seconds"] <= cap
    with env.admin.begin() as conn:  # the delay passes (simulated by ageing the attempts)
        conn.execute(
            text("UPDATE auth_attempts SET at = at - make_interval(secs => :s)"), {"s": cap + 1}
        )
    r = _peer(env, "10.5.0.99").post(
        "/api/v1/auth/login", json={"email": email, "password": PASSWORD}
    )
    assert r.status_code == 200


# --------------------------------------------------------------------------- B2-S05


def test_b2_s05_one_answer_for_every_wrong_credential(env: Env) -> None:
    firm = env.firm()
    unenrolled, _, _ = _seed(env, firm, enrolled=False)
    enrolled, _, _ = _seed(env, firm)
    with env.admin.begin() as conn:
        disabled, _, uid = _seed(env, firm)
        conn.execute(text("UPDATE users SET disabled_at = now() WHERE id = :u"), {"u": uid})
    answers = {
        "unenrolled, right password": _login(env, unenrolled),
        "enrolled, wrong password": _login(env, enrolled, "definitely-wrong-123"),
        "disabled, right password": _login(env, disabled),
        "absent address": _login(env, f"absent.{uuid.uuid4().hex[:8]}@firm.test"),
    }
    for label, r in answers.items():
        assert (r.status_code, r.json()) == (401, {"reason": "sign_in_failed"}), label
        assert "set-cookie" not in r.headers, label


def test_b2_s05_invitation_does_not_reveal_accounts_at_other_firms(
    env: Env, _mail: None, addresses: list[str]
) -> None:
    a, b = env.firm("A"), env.firm("B")
    m = _join(env, a, _addr(addresses, "member"))
    c = env.client
    r = c.post("/api/v1/invites", headers=b.h(), json={"email": m.email, "role": "preparer"})
    assert r.status_code == 201  # same answer as for an address nobody uses
    tok = mailpit.link_token(mailpit.latest_text(m.email, count=2), "invite")
    r = c.post(f"/api/v1/invites/{tok}/accept", json={"password": "another-long-pass-7"})
    assert r.status_code == 409 and r.json()["reason"] == "address_has_an_account"
    # Inside one firm the Owner already sees its users, so the clash is said there.
    r = c.post("/api/v1/invites", headers=a.h(), json={"email": m.email, "role": "preparer"})
    assert r.status_code == 409


# --------------------------------------------------------------------------- B2-S06


@pytest.mark.parametrize("sep", [",", ";"])
def test_b2_s06_no_cell_reads_as_a_formula_in_comma_or_semicolon_locales(sep: str) -> None:
    values = ["=1+1", "+1", "-1", "@SUM(A1)", "\t=1", "\r=1", "\n=1+1", " =1+1", "＝1+1",
              "a;=1+1", "a;=cmd|' /C calc'!A0", "a,=1", "x; @x", "plain"]  # fmt: skip
    data = csv_bytes(["v"], [[v] for v in values]).decode("utf-8-sig")
    assert all(line.startswith('"') for line in data.split("\r\n") if line)  # every field quoted
    # A reader with this list separator, then the naive one that ignores quotes.
    quoted = [row[0] for row in csv.reader(io.StringIO(data), delimiter=sep)][1:]
    naive = [cell for line in data.split("\r\n")[1:] for cell in line.split(sep)]
    for cell in quoted + naive:
        bare = cell.strip().strip('"').lstrip(" \t\r\n")
        assert not bare.startswith(("=", "+", "-", "@", "＝")), (sep, cell)
    assert safe_cell("plain") == "plain" and safe_cell('=HYPERLINK("x")').startswith("'")
    # Embedded quotes stay one quoted field for a reader that honours quoting.
    one = csv_bytes(["v"], [['x","=1+1']]).decode("utf-8-sig")
    assert next(iter(list(csv.reader(io.StringIO(one), delimiter=sep))[1:]))[0] == 'x","=1+1'


def test_b2_s01_code_reuse_still_refused_across_sessions(env: Env, _mail: None) -> None:
    """Guard that the reservation did not loosen the replay rule."""
    firm = env.firm()
    m = _join(env, firm, f"replay.{uuid.uuid4().hex[:10]}@firm.test")
    c = env.client
    code = _code(env, m.secret, 1)
    a, b = _cookie(_login(env, m.email)), _cookie(_login(env, m.email))
    c.cookies.clear()
    assert c.post("/api/v1/auth/totp", headers=_h(a), json={"code": code}).status_code == 200
    assert c.post("/api/v1/auth/totp", headers=_h(b), json={"code": code}).status_code == 401
    mailpit.delete_to(m.email)
