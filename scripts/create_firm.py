"""Vendor onboarding: create a firm and invite its first Owner (TRD 8.1; B2).

    python scripts/create_firm.py --name "<legal name>" --owner-email <email>

The invitation is e-mailed through the configured SMTP server (locally Mailpit). The firm
row is written with PINTAE_ADMIN_DATABASE_URL (the application role cannot create firms);
the invitation through the application role and the firm's tenancy session.
"""

from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [
    str(ROOT / p)
    for p in ("packages/core", "packages/rules", "packages/rulepacks", "packages/ingest")
]


def main() -> int:
    from sqlalchemy import text

    from pintae_core import identity
    from pintae_core.db import admin_engine, app_engine
    from pintae_core.mail import default_mailer
    from pintae_core.readiness import DomainError

    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--owner-email", required=True)
    args = ap.parse_args()
    fid = uuid.uuid4()
    with admin_engine().begin() as conn:
        conn.execute(
            text("INSERT INTO firms (id, legal_name) VALUES (:i, :n)"), {"i": fid, "n": args.name}
        )
    try:
        identity.create_invite(
            app_engine(),
            default_mailer(),
            firm_id=fid,
            actor_id=None,
            email=args.owner_email,
            role="owner",
        )
    except DomainError as exc:
        print(f"refused: {exc.reason}", file=sys.stderr)
        return 1
    print(f"firm {fid} created; Owner invitation sent to {args.owner_email}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
