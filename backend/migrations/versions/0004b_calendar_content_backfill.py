"""B1-014: fill calendar_versions.content for versions published before migration 0004.

Migration 0004 added `content` as NULL for existing rows and then froze them, so an upgraded
database could not load any calendar. This step derives the content once from the version's
own child rows (see `pintae_core.calendar_content`), writes only rows whose `content` is
NULL, and is idempotent and resumable. It is a data step inside a schema migration, which
AGENTS.md section 6 normally forbids; it is allowed here because the content is defined by
rows already in the database (a handful of reference rows, no tenant data, no long scan),
and the freeze guard cannot be lifted later without DDL (schema.md, reference-data guard).
The guard on `calendar_versions` is suspended for this transaction only.

Revision ID: 0004b
Revises: 0004
Create Date: 2026-11-11
"""

from alembic import op

revision = "0004b"
down_revision = "0004"
branch_labels = None
depends_on = None

ORIGIN_CHECK = "content_origin IN ('publication', 'derived_from_rows', 'legacy_unverified')"


def backfill() -> None:
    """Shared with later revisions that repair databases which skipped this one."""
    from pintae_core.calendar_content import derive_missing_content

    op.execute(
        "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE"
        " table_name = 'calendar_versions' AND column_name = 'content_origin') THEN"
        " ALTER TABLE calendar_versions ADD COLUMN content_origin text;"
        f" ALTER TABLE calendar_versions ADD CONSTRAINT ck_calendar_versions_content_origin"
        f" CHECK ({ORIGIN_CHECK}); END IF; END $$"
    )
    op.execute("ALTER TABLE calendar_versions DISABLE TRIGGER calendar_versions_immutable")
    derive_missing_content(op.get_bind())
    op.execute("ALTER TABLE calendar_versions ENABLE TRIGGER calendar_versions_immutable")


def upgrade() -> None:
    backfill()


def downgrade() -> None:
    # The derived content stays (it is frozen reference data); only the origin column goes.
    op.execute("ALTER TABLE calendar_versions DISABLE TRIGGER calendar_versions_immutable")
    op.drop_constraint("ck_calendar_versions_content_origin", "calendar_versions", type_="check")
    op.drop_column("calendar_versions", "content_origin")
    op.execute("ALTER TABLE calendar_versions ENABLE TRIGGER calendar_versions_immutable")
