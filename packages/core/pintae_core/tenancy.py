"""The tenancy session (TRD 8.2, R-05). The only way the API and the worker open a database
session. Row-level security keys on the transaction-local ``app.firm_id`` setting, so a
session without a firm sees zero tenant rows.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from pintae_core.db import app_engine


@contextmanager
def session(firm_id: uuid.UUID, engine: Engine | None = None) -> Iterator[Session]:
    """One transaction scoped to one firm. Commits on success, rolls back on error."""
    eng = engine or app_engine()
    with Session(eng, expire_on_commit=False) as s, s.begin():
        s.execute(text("SELECT set_config('app.firm_id', :f, true)"), {"f": str(firm_id)})
        yield s


@contextmanager
def reference_session(engine: Engine | None = None) -> Iterator[Session]:
    """Read-only access to global reference tables (packs, calendars). No firm is set, so
    tenant tables return nothing."""
    eng = engine or app_engine()
    with Session(eng, expire_on_commit=False) as s, s.begin():
        s.execute(text("SET TRANSACTION READ ONLY"))
        yield s
