"""Read the local Mailpit inbox (http://127.0.0.1:8025/api/v1) in integration tests."""

from __future__ import annotations

import re
import time

import httpx
import pytest

API = "http://127.0.0.1:8025/api/v1"


def available() -> bool:
    try:
        return httpx.get(f"{API}/messages", params={"limit": 1}, timeout=2).status_code == 200
    except httpx.HTTPError:
        return False


def require() -> None:
    if not available():
        pytest.skip("Mailpit is not running at 127.0.0.1:8025")


def messages_to(address: str) -> list[dict[str, object]]:
    r = httpx.get(f"{API}/search", params={"query": f'to:"{address}"'}, timeout=5)
    r.raise_for_status()
    msgs: list[dict[str, object]] = r.json().get("messages") or []
    return msgs


def latest_text(address: str, *, count: int = 1, wait_s: float = 5.0) -> str:
    """The plain-text body of the newest message to ``address`` once ``count`` exist."""
    deadline = time.monotonic() + wait_s
    while True:
        msgs = messages_to(address)
        if len(msgs) >= count:
            mid = msgs[0]["ID"]
            r = httpx.get(f"{API}/message/{mid}", timeout=5)
            r.raise_for_status()
            text: str = r.json()["Text"]
            return text
        if time.monotonic() > deadline:
            raise AssertionError(f"no message for {address} in Mailpit")
        time.sleep(0.1)


def link_token(body: str, path: str) -> str:
    m = re.search(rf"/{path}/([A-Za-z0-9_\-]+)", body)
    assert m, body
    return m.group(1)


def delete_to(address: str) -> None:
    ids = [m["ID"] for m in messages_to(address)]
    if ids:
        httpx.request("DELETE", f"{API}/messages", json={"IDs": ids}, timeout=5)
