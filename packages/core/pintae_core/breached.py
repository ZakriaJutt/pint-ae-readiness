"""Offline breached-password check (ASVS 6.2.12, partial).

A small built-in set of passwords of 12 or more characters that appear at the top of public
breach corpora, plus patterns that such lists are dominated by (one repeated character, a
keyboard or digit run). A full corpus or the k-anonymity range service is an external
dependency and is deferred (verification-report-fixing.md section 10).
"""

from __future__ import annotations

_COMMON = frozenset(
    {
        "123456789012",
        "1234567890123",
        "12345678901234",
        "123456789123",
        "123123123123",
        "111111111111",
        "000000000000",
        "password1234",
        "password12345",
        "password123456",
        "password@123",
        "password!123",
        "passw0rd1234",
        "p@ssw0rd1234",
        "p@ssword1234",
        "qwertyuiop12",
        "qwertyuiopas",
        "qwerty123456",
        "qwertyuiop123",
        "1q2w3e4r5t6y",
        "1qaz2wsx3edc",
        "zaq12wsxcde3",
        "asdfghjkl123",
        "iloveyou1234",
        "letmein12345",
        "welcome12345",
        "welcome@1234",
        "admin1234567",
        "administrator",
        "administrator1",
        "changeme1234",
        "football1234",
        "baseball1234",
        "monkey123456",
        "sunshine1234",
        "princess1234",
        "dragon123456",
        "superman1234",
        "trustno11234",
        "abc123456789",
        "abcdefghijkl",
        "abcd12345678",
        "aa1234567890",
        "q1w2e3r4t5y6",
        "passwordpassword",
        "dubai1234567",
        "emirates1234",
        "uae123456789",
    }
)

_RUNS = ("0123456789", "9876543210", "qwertyuiop", "asdfghjkl", "zxcvbnm", "abcdefghijklmnop")


def is_breached(password: str) -> bool:
    p = password.casefold()
    if p in _COMMON:
        return True
    if len(set(p)) <= 2:
        return True
    return any(p in (run * 3) for run in _RUNS)
