"""Validate and publish a rule pack or calendar file (execution-plan section 5, TRD 8.4).

    python scripts/load_rulepack.py <file.json> --publisher-email <email> [--confirm-hash <hex>]

Refuses on failed fixtures, changed content under an existing code, or missing source
references. Without ``--confirm-hash`` it only validates and prints the hash the publisher
must confirm (step 2 of the two-step publication). Uses PINTAE_ADMIN_DATABASE_URL.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [
    str(ROOT / p)
    for p in ("packages/core", "packages/rules", "packages/rulepacks", "packages/ingest")
]


def main() -> int:
    from pintae_core.config import get_settings
    from pintae_core.db import admin_engine
    from pintae_core.publication import (
        PublicationRefused,
        ensure_publisher,
        publish_calendar,
        publish_rule_pack,
    )
    from pintae_rulepacks import fixture_path
    from pintae_rules.packs import PackError, content_hash, pack_from_data

    ap = argparse.ArgumentParser()
    ap.add_argument("file", type=Path)
    ap.add_argument("--publisher-email", required=True)
    ap.add_argument("--confirm-hash")
    args = ap.parse_args()
    if get_settings().env == "production":
        print("refused: publication from this script is for local and staging use", file=sys.stderr)
        return 2
    data = json.loads(args.file.read_text(encoding="utf-8"))
    digest = content_hash(data).hex()
    kind = data.get("object_type")
    if kind == "rule_pack":
        try:
            pack_from_data(data)
        except PackError as exc:
            print(f"refused: {exc}", file=sys.stderr)
            return 1
    if not args.confirm_hash:
        print(
            f"{kind} {data.get('code')} content hash {digest}: re-run with --confirm-hash to publish"
        )
        return 0
    engine = admin_engine()
    publisher = ensure_publisher(engine, args.publisher_email)
    try:
        if kind == "rule_pack":
            fx = (
                json.loads(fixture_path(data["code"]).read_text())
                if fixture_path(data["code"]).exists()
                else []
            )
            publish_rule_pack(engine, data, fx, publisher, bytes.fromhex(args.confirm_hash))
        elif kind == "calendar_version":
            publish_calendar(engine, data, publisher, bytes.fromhex(args.confirm_hash))
        else:
            print("refused: object_type must be rule_pack or calendar_version", file=sys.stderr)
            return 1
    except PublicationRefused as exc:
        print(f"refused: {exc.reason} {exc.detail or ''}", file=sys.stderr)
        return 1
    print(f"published {data['code']} ({digest})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
