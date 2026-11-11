"""B1-014 on databases that reached 0005 before 0004b existed (for example `pintae_dev`).

Alembic treats 0004b as applied on such a database, because 0005 now follows it. This step
repeats 0004b: it adds `calendar_versions.content_origin` if missing and fills `content`
once where it is NULL, from the version's own rows (`pintae_core.calendar_content`). On any
other database it changes nothing. Idempotent and resumable; see 0004b for why a data step
is allowed here.

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-11
"""

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

ORIGIN_CHECK = "content_origin IN ('publication', 'derived_from_rows', 'legacy_unverified')"


def upgrade() -> None:
    from pintae_core.calendar_content import derive_missing_content

    op.execute(
        "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE"
        " table_name = 'calendar_versions' AND column_name = 'content_origin') THEN"
        " ALTER TABLE calendar_versions ADD COLUMN content_origin text;"
        " ALTER TABLE calendar_versions ADD CONSTRAINT ck_calendar_versions_content_origin"
        f" CHECK ({ORIGIN_CHECK}); END IF; END $$"
    )
    op.execute("ALTER TABLE calendar_versions DISABLE TRIGGER calendar_versions_immutable")
    derive_missing_content(op.get_bind())
    op.execute("ALTER TABLE calendar_versions ENABLE TRIGGER calendar_versions_immutable")


def downgrade() -> None:
    pass  # nothing to undo: the repaired content is frozen reference data
