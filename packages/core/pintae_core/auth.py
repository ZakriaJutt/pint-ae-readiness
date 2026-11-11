"""Sign-in primitives (TRD 8.1, B2): password hashing and policy, TOTP, the encryption of
TOTP secrets, opaque tokens, anti-forgery tokens and recovery codes. Pure functions; the
flows that use them are in ``pintae_core.identity``.

ASVS 5.0.0 references are listed in TRD 8.8 and verification-report-fixing.md section 10.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import uuid
from datetime import datetime

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from pintae_core.breached import is_breached
from pintae_core.config import get_settings

# --------------------------------------------------------------------------- passwords

MIN_PASSWORD = 12  # ASVS 6.2.1
MAX_PASSWORD = 128  # long passphrases are allowed
_SCRYPT_N, _SCRYPT_R, _SCRYPT_P = 2**15, 8, 1


def password_problems(password: str, email: str | None = None) -> list[str]:
    """Reasons a new password is refused; empty when it is accepted. No composition rules:
    length and the breached-password set only (ASVS 6.2.1, 6.2.12)."""
    out: list[str] = []
    if len(password) < MIN_PASSWORD:
        out.append("too_short")
    if len(password) > MAX_PASSWORD:
        out.append("too_long")
    if is_breached(password):
        out.append("breached_password")
    if email and password.casefold() == email.casefold():
        out.append("same_as_email")
    return out


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(
        password.encode(), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, maxmem=2**26, dklen=32
    )
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt_b64, dk_b64 = stored.split("$")
    except ValueError:
        return False
    if scheme != "scrypt":
        return False
    dk = hashlib.scrypt(
        password.encode(),
        salt=base64.b64decode(salt_b64),
        n=int(n),
        r=int(r),
        p=int(p),
        maxmem=2**26,
        dklen=32,
    )
    return hmac.compare_digest(dk, base64.b64decode(dk_b64))


# A hash of a random password: verified when the account does not exist, so that the
# password step takes the same time either way.
_DUMMY = hash_password(secrets.token_urlsafe(16))


def burn_password_check(password: str) -> None:
    verify_password(password, _DUMMY)


# --------------------------------------------------------------------------- TOTP (RFC 6238)

TOTP_STEP_SECONDS = 30
TOTP_DIGITS = 6
TOTP_WINDOW = 1  # one step either side for clock drift


def new_totp_secret() -> bytes:
    return secrets.token_bytes(20)  # 160 bits, RFC 4226 recommendation


def totp_secret_b32(secret: bytes) -> str:
    return base64.b32encode(secret).decode().rstrip("=")


def otpauth_uri(secret: bytes, email: str) -> str:
    from urllib.parse import quote

    label = quote(f"PINT AE Readiness Desk:{email}")
    return (
        f"otpauth://totp/{label}?secret={totp_secret_b32(secret)}"
        "&issuer=PINT%20AE%20Readiness%20Desk&algorithm=SHA1&digits=6&period=30"
    )


def totp_step(at: datetime) -> int:
    return int(at.timestamp()) // TOTP_STEP_SECONDS


def totp_code(secret: bytes, step: int) -> str:
    mac = hmac.new(secret, struct.pack(">Q", step), hashlib.sha1).digest()
    off = mac[-1] & 0x0F
    value = struct.unpack(">I", mac[off : off + 4])[0] & 0x7FFFFFFF
    return str(value % 10**TOTP_DIGITS).zfill(TOTP_DIGITS)


def verify_totp(secret: bytes, code: str, at: datetime, last_step: int | None) -> int | None:
    """The matching time step, or None. A step at or before ``last_step`` is refused, so a
    code is accepted once only (ASVS 6.5.1 replay)."""
    code = code.strip().replace(" ", "")
    if len(code) != TOTP_DIGITS or not code.isdigit():
        return None
    now = totp_step(at)
    for step in range(now - TOTP_WINDOW, now + TOTP_WINDOW + 1):
        if last_step is not None and step <= last_step:
            continue
        if hmac.compare_digest(totp_code(secret, step), code):
            return step
    return None


# --------------------------------------------------------------------------- secret box


def _aead() -> AESGCM:
    return AESGCM(base64.b64decode(get_settings().totp_key))


def seal_totp_secret(secret: bytes, user_id: uuid.UUID) -> bytes:
    """AES-256-GCM, bound to the user id so a sealed secret cannot be moved to another row."""
    nonce = secrets.token_bytes(12)
    return b"\x01" + nonce + _aead().encrypt(nonce, secret, user_id.bytes)


def open_totp_secret(sealed: bytes, user_id: uuid.UUID) -> bytes | None:
    if len(sealed) < 30 or sealed[:1] != b"\x01":
        return None
    try:
        return _aead().decrypt(sealed[1:13], sealed[13:], user_id.bytes)
    except InvalidTag:
        return None


# --------------------------------------------------------------------------- tokens


def new_token() -> str:
    """Opaque token, 256 bits from the operating system's generator (ASVS 7.2.3)."""
    return secrets.token_urlsafe(32)


def token_hash(token: str) -> bytes:
    return hashlib.sha256(token.encode()).digest()


def csrf_token(session_token: str) -> str:
    """Anti-forgery token tied to the session (ASVS 3.5.1); changes when the session does."""
    key = get_settings().secret_key.encode()
    return hmac.new(key, b"csrf:" + session_token.encode(), hashlib.sha256).hexdigest()


def csrf_ok(session_token: str, presented: str | None) -> bool:
    return bool(presented) and hmac.compare_digest(csrf_token(session_token), presented or "")


def throttle_key(kind: str, value: str) -> bytes:
    """Keyed hash of an e-mail address or a client address: the value is never stored."""
    key = get_settings().secret_key.encode()
    return hmac.new(key, f"{kind}:{value.casefold()}".encode(), hashlib.sha256).digest()


# --------------------------------------------------------------------------- recovery codes

RECOVERY_CODES = 10
_ALPHABET = "ABCDEFGHJKMNPQRSTVWXYZ23456789"  # no 0/O, 1/I/L, U


def new_recovery_codes() -> list[str]:
    """Ten single-use codes, 50 bits each from the secure generator (ASVS 6.5.2, 6.5.3)."""
    out = []
    for _ in range(RECOVERY_CODES):
        raw = "".join(secrets.choice(_ALPHABET) for _ in range(10))
        out.append(f"{raw[:5]}-{raw[5:]}")
    return out


def normalise_recovery_code(code: str) -> str:
    return code.strip().upper().replace(" ", "").replace("-", "")


def hash_recovery_code(code: str) -> str:
    return hash_password(normalise_recovery_code(code))


def verify_recovery_code(code: str, stored: str) -> bool:
    return verify_password(normalise_recovery_code(code), stored)
