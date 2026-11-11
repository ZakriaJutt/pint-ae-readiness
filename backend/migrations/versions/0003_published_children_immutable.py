"""B1-012: rows that belong to a published rule pack or calendar version are immutable.

`rules` (severity, applicability), `calendar_rules` (dates) and `provisions` (grace periods)
are read by the status function and the calendar. Once the parent is published (or later
withdrawn), UPDATE and DELETE are refused, for the owner role too, and INSERT is accepted
only inside the publishing transaction itself (parent created in this transaction). A change
requires a new pack or calendar version.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-11
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

FUNC = r"""
CREATE OR REPLACE FUNCTION pintae_published_child_immutable() RETURNS trigger
LANGUAGE plpgsql AS $f$
DECLARE
  parent_table text := TG_ARGV[0];
  parent_col text := TG_ARGV[1];
  pid uuid;
  pstatus text;
  pcreated timestamptz;
BEGIN
  IF TG_OP = 'DELETE' THEN
    pid := (to_jsonb(OLD) ->> parent_col)::uuid;
  ELSE
    pid := (to_jsonb(NEW) ->> parent_col)::uuid;
  END IF;
  EXECUTE format('SELECT status, created_at FROM %I WHERE id = $1', parent_table)
    INTO pstatus, pcreated USING pid;
  IF pstatus IN ('published', 'withdrawn') THEN
    IF TG_OP = 'INSERT' AND pcreated = now() THEN
      RETURN NEW;  -- the publishing transaction writes its own children
    END IF;
    RAISE EXCEPTION '% of a published % is immutable; publish a new version',
      TG_TABLE_NAME, parent_table USING ERRCODE = '42501';
  END IF;
  IF TG_OP = 'DELETE' THEN
    RETURN OLD;
  END IF;
  RETURN NEW;
END $f$;
"""

TRIGGERS = (
    ("rules", "rule_packs", "rule_pack_id"),
    ("calendar_rules", "calendar_versions", "calendar_version_id"),
    ("provisions", "calendar_versions", "calendar_version_id"),
)


def upgrade() -> None:
    op.execute(FUNC)
    for table, parent, col in TRIGGERS:
        op.execute(
            f"CREATE TRIGGER {table}_published_immutable BEFORE INSERT OR UPDATE OR DELETE "
            f"ON {table} FOR EACH ROW EXECUTE FUNCTION "
            f"pintae_published_child_immutable('{parent}', '{col}')"
        )


def downgrade() -> None:
    for table, _, _ in TRIGGERS:
        op.execute(f"DROP TRIGGER IF EXISTS {table}_published_immutable ON {table}")
    op.execute("DROP FUNCTION IF EXISTS pintae_published_child_immutable()")
