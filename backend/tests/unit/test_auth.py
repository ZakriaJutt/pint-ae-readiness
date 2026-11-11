"""B2 sign-in primitives: TOTP (RFC 6238 vectors), password policy and hashing, secret
sealing, anti-forgery tokens, recovery codes, CSV formula escaping, storage keys."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from pintae_core import auth
from pintae_core.exports import csv_bytes, safe_cell
from pintae_core.storage import check_key, generated_key, upload_key

RFC_SECRET = b"12345678901234567890"


@pytest.mark.parametrize(
    "t,code",
    [(59, "287082"), (1111111109, "081804"), (1111111111, "050471"), (1234567890, "005924"),
     (2000000000, "279037"), (20000000000, "353130")],
)  # fmt: skip
def test_totp_matches_rfc6238_sha1_vectors(t: int, code: str) -> None:
    # RFC 6238 appendix B gives 8 digits; the last six are the 6-digit code.
    assert auth.totp_code(RFC_SECRET, t // 30) == code


def test_totp_window_and_replay_guard() -> None:
    at = datetime(2026, 11, 11, 8, 0, 15, tzinfo=UTC)
    step = auth.totp_step(at)
    code = auth.totp_code(RFC_SECRET, step)
    assert auth.verify_totp(RFC_SECRET, code, at, None) == step
    assert auth.verify_totp(RFC_SECRET, code[:3] + " " + code[3:], at, None) == step
    assert auth.verify_totp(RFC_SECRET, code, at, step) is None  # used once only
    prev = auth.totp_code(RFC_SECRET, step - 1)
    assert auth.verify_totp(RFC_SECRET, prev, at, None) == step - 1  # one step of drift
    assert auth.verify_totp(RFC_SECRET, auth.totp_code(RFC_SECRET, step - 2), at, None) is None
    assert auth.verify_totp(RFC_SECRET, "12345", at, None) is None
    assert auth.verify_totp(RFC_SECRET, "abcdef", at, None) is None


def test_password_policy_length_and_breached_set() -> None:
    assert auth.password_problems("short-pass") == ["too_short"]
    assert "breached_password" in auth.password_problems("Password1234")
    assert "breached_password" in auth.password_problems("aaaaaaaaaaaaaaaa")
    assert "breached_password" in auth.password_problems("1234567890123456")
    assert auth.password_problems("x" * 129)[0] == "too_long"
    assert auth.password_problems("a@firm.test", "A@FIRM.TEST") == ["too_short", "same_as_email"]
    assert auth.password_problems("correct horse battery staple") == []


def test_password_hash_is_salted_and_verifies() -> None:
    h1, h2 = (
        auth.hash_password("correct horse battery"),
        auth.hash_password("correct horse battery"),
    )
    assert h1 != h2 and h1.startswith("scrypt$")
    assert auth.verify_password("correct horse battery", h1)
    assert not auth.verify_password("correct horse batterz", h1)
    assert not auth.verify_password("x", "!test")


def test_totp_secret_sealed_and_bound_to_user() -> None:
    u1, u2 = uuid.uuid4(), uuid.uuid4()
    sealed = auth.seal_totp_secret(RFC_SECRET, u1)
    assert RFC_SECRET not in sealed
    assert auth.open_totp_secret(sealed, u1) == RFC_SECRET
    assert auth.open_totp_secret(sealed, u2) is None
    assert auth.open_totp_secret(b"\x00", u1) is None


def test_tokens_and_anti_forgery() -> None:
    t1, t2 = auth.new_token(), auth.new_token()
    assert t1 != t2 and len(t1) >= 43  # 256 bits
    assert auth.csrf_ok(t1, auth.csrf_token(t1))
    assert not auth.csrf_ok(t1, auth.csrf_token(t2))
    assert not auth.csrf_ok(t1, None)
    assert auth.throttle_key("account", "A@x.test") == auth.throttle_key("account", "a@x.test")


def test_recovery_codes_single_set_of_ten_and_normalised() -> None:
    codes = auth.new_recovery_codes()
    assert len(set(codes)) == 10
    stored = auth.hash_recovery_code(codes[0])
    assert auth.verify_recovery_code(codes[0].lower().replace("-", " "), stored)
    assert not auth.verify_recovery_code(codes[1], stored)


def test_ut15_csv_cells_that_start_a_formula_are_escaped() -> None:
    assert safe_cell('=HYPERLINK("x")') == '\'=HYPERLINK("x")'  # UT-15
    assert [safe_cell(v) for v in ("=1+1", "+9", "-2", "@x", "ok", None, 5)] == [
        "'=1+1", "'+9", "'-2", "'@x", "ok", "", "5",
    ]  # fmt: skip
    assert csv_bytes(["a"], [["=cmd"]]).decode("utf-8-sig") == "a\r\n'=cmd\r\n"


def test_storage_keys_isolate_firm_source_and_purpose() -> None:
    f, e = uuid.uuid4(), uuid.uuid4()
    k = upload_key(f, e, "invoices")
    assert k.startswith(f"firms/{f}/entities/{e}/source-invoices/")
    assert generated_key(f, "fix_list").startswith(f"firms/{f}/generated/fix_list/")
    with pytest.raises(ValueError):
        generated_key(f, "anything")
    for bad in ("../x", "firms/not-a-uuid/a/b", f"firms/{f}/../x/y", "/firms/x", f"firms/{f}//x"):
        with pytest.raises(ValueError):
            check_key(bad)
