"""Work done after the response (B2-S03): a single in-process worker thread.

Used for the password-reset request, so that the answer takes the same time and says the
same thing whether or not the address has an account; the reset row, the audit event and the
SMTP send all happen here. Queued work is lost if the process stops before it runs; the user
then asks again. No secret is written anywhere while it waits.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor

from pintae_core.logging import log_event

log = logging.getLogger("pintae.background")
_lock = threading.Lock()
_pool: ThreadPoolExecutor | None = None
_pending: set[Future[None]] = set()


def _executor() -> ThreadPoolExecutor:
    global _pool
    with _lock:
        if _pool is None:
            _pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="pintae-bg")
        return _pool


def _run(fn: Callable[[], None]) -> None:
    try:
        fn()
    except Exception as exc:  # logged by type only: no values, no addresses
        log_event(log, "background.failed", reason_code=type(exc).__name__)


def submit(fn: Callable[[], None]) -> None:
    fut: Future[None] = _executor().submit(_run, fn)
    with _lock:
        _pending.add(fut)
    fut.add_done_callback(lambda f: _pending.discard(f))


def wait_idle(timeout: float = 10.0) -> None:
    """Tests: wait until queued work has run."""
    with _lock:
        futs = list(_pending)
    for f in futs:
        f.result(timeout=timeout)
