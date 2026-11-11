"""C1 (2026-11-11), IT-22: CAL-3 (PRV-2 re-sourced to Ministerial Decision 197 of 2026)
publishes through the two-step publication path, becomes the current calendar, and its
provision rows carry the MD 197 source. The conftest cleanup removes CAL-3 afterwards."""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from pintae_core import readiness
from pintae_core.publication import publish_calendar
from pintae_rulepacks import load_data
from pintae_rules.packs import content_hash
from tests.integration.conftest import Env


def test_it22_cal3_publishes_and_is_current_with_md197_source(env: Env) -> None:
    data = load_data("CAL-3")
    publish_calendar(env.admin, data, env.publisher_id, content_hash(data))
    with env.admin.connect() as conn:
        s = Session(bind=conn)
        cur = readiness.current_calendar(s)
        assert cur.code == "CAL-3"
        prv2 = next(p for p in cur.provisions if p.code == "PRV-2")
        assert (prv2.applies_from, prv2.applies_to) == (date(2027, 1, 1), date(2028, 12, 31))
        assert prv2.source_refs[0].startswith("SRC-25")
        # Dates are unchanged from CAL-2: the correction is the legal basis, not a deadline.
        assert cur.rule("SEG-L").appoint_by == date(2026, 10, 30)
        assert cur.rule("SEG-S").appoint_by == date(2027, 3, 31)
