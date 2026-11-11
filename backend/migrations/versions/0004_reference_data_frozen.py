"""B1-012 round 3 (X3-X6): published reference data is frozen for good.

- `rule_packs` and `calendar_versions`: a published or withdrawn row never changes apart from
  the one transition published -> withdrawn. Withdrawn is terminal. A draft is never turned
  into a publication by UPDATE: publication inserts a new version (a new code).
- `rules`, `calendar_rules`, `provisions`: UPDATE and DELETE are refused when the OLD or the
  NEW parent is published or withdrawn (X4: a child cannot be moved out to a draft parent).
- `publications`: UPDATE and DELETE are always refused.
- BEFORE TRUNCATE statement triggers refuse TRUNCATE on all six tables, for every role (X3).
- Privileges: UPDATE, DELETE and TRUNCATE are revoked from PUBLIC, `pintae_app` and the owner
  role that runs migrations and publication; the owner keeps UPDATE on the `status` column of
  the two parent tables only, for withdrawal. (A superuser owner is not subject to privilege
  checks; for it the triggers are the guard.)
- `calendar_versions.content`: the calendar file as published, so loaders can recompute
  `content_hash(content)` and refuse a mismatch, as for rule packs.

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-11
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

PARENTS = ("rule_packs", "calendar_versions")
CHILDREN = (
    ("rules", "rule_packs", "rule_pack_id"),
    ("calendar_rules", "calendar_versions", "calendar_version_id"),
    ("provisions", "calendar_versions", "calendar_version_id"),
)
GUARDED = ("rule_packs", "rules", "calendar_versions", "calendar_rules", "provisions", "publications")

PARENT_FUNC = r"""
CREATE OR REPLACE FUNCTION pintae_published_immutable() RETURNS trigger
LANGUAGE plpgsql AS $f$
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'reference data % cannot be deleted; publish a new version', OLD.code
      USING ERRCODE = '42501';
  END IF;
  IF OLD.status = 'draft' THEN
    IF NEW.status <> 'draft' THEN
      RAISE EXCEPTION 'draft % is immutable as a publication: publish a new version through '
        'the publication path', OLD.code USING ERRCODE = '42501';
    END IF;
    RETURN NEW;
  END IF;
  -- Published or withdrawn: every column except status is frozen, for good.
  IF (to_jsonb(NEW) - 'status') IS DISTINCT FROM (to_jsonb(OLD) - 'status') THEN
    RAISE EXCEPTION '% % is immutable; publish a new version', OLD.status, OLD.code
      USING ERRCODE = '42501';
  END IF;
  IF OLD.status = 'withdrawn' AND NEW.status <> 'withdrawn' THEN
    RAISE EXCEPTION 'withdrawn % is immutable and terminal; publish a new version', OLD.code
      USING ERRCODE = '42501';
  END IF;
  IF OLD.status = 'published' AND NEW.status NOT IN ('published', 'withdrawn') THEN
    RAISE EXCEPTION 'published % is immutable and can only be withdrawn', OLD.code
      USING ERRCODE = '42501';
  END IF;
  RETURN NEW;
END $f$;
"""

CHILD_FUNC = r"""
CREATE OR REPLACE FUNCTION pintae_published_child_immutable() RETURNS trigger
LANGUAGE plpgsql AS $f$
DECLARE
  parent_table text := TG_ARGV[0];
  parent_col text := TG_ARGV[1];
  pstatus text;
  pcreated timestamptz;
BEGIN
  IF TG_OP IN ('UPDATE', 'DELETE') THEN
    EXECUTE format('SELECT status FROM %I WHERE id = $1', parent_table)
      INTO pstatus USING (to_jsonb(OLD) ->> parent_col)::uuid;
    IF pstatus IN ('published', 'withdrawn') THEN
      RAISE EXCEPTION '% of a published % is immutable; publish a new version',
        TG_TABLE_NAME, parent_table USING ERRCODE = '42501';
    END IF;
  END IF;
  IF TG_OP IN ('INSERT', 'UPDATE') THEN
    EXECUTE format('SELECT status, created_at FROM %I WHERE id = $1', parent_table)
      INTO pstatus, pcreated USING (to_jsonb(NEW) ->> parent_col)::uuid;
    IF pstatus IN ('published', 'withdrawn') THEN
      IF TG_OP = 'INSERT' AND pcreated = now() THEN
        RETURN NEW;  -- the publishing transaction writes its own children
      END IF;
      RAISE EXCEPTION '% of a published % is immutable; publish a new version',
        TG_TABLE_NAME, parent_table USING ERRCODE = '42501';
    END IF;
    RETURN NEW;
  END IF;
  RETURN OLD;
END $f$;
"""

OTHER_FUNCS = r"""
CREATE OR REPLACE FUNCTION pintae_reference_no_truncate() RETURNS trigger
LANGUAGE plpgsql AS $f$
BEGIN
  RAISE EXCEPTION '% is immutable reference data; TRUNCATE is refused', TG_TABLE_NAME
    USING ERRCODE = '42501';
END $f$;
CREATE OR REPLACE FUNCTION pintae_publication_immutable() RETURNS trigger
LANGUAGE plpgsql AS $f$
BEGIN
  RAISE EXCEPTION 'publication records are immutable' USING ERRCODE = '42501';
END $f$;
"""

# The 0003 child function, restored on downgrade.
OLD_CHILD_FUNC = r"""
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
      RETURN NEW;
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

# The 0001 parent function, restored on downgrade.
OLD_PARENT_FUNC = r"""
CREATE OR REPLACE FUNCTION pintae_published_immutable() RETURNS trigger
LANGUAGE plpgsql AS $f$
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'published reference data cannot be deleted' USING ERRCODE = '42501';
  END IF;
  IF OLD.status = 'published' AND (to_jsonb(NEW) - 'status') IS DISTINCT FROM (to_jsonb(OLD) - 'status') THEN
    RAISE EXCEPTION 'published % is immutable; publish a new version', OLD.code USING ERRCODE = '42501';
  END IF;
  IF OLD.status = 'published' AND NEW.status NOT IN ('published', 'withdrawn') THEN
    RAISE EXCEPTION 'published % can only be withdrawn', OLD.code USING ERRCODE = '42501';
  END IF;
  RETURN NEW;
END $f$;
"""


def upgrade() -> None:
    op.add_column(
        "calendar_versions",
        sa.Column("content", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.execute(PARENT_FUNC)
    op.execute(CHILD_FUNC)
    op.execute(OTHER_FUNCS)
    op.execute(
        "CREATE TRIGGER publications_immutable BEFORE UPDATE OR DELETE ON publications "
        "FOR EACH ROW EXECUTE FUNCTION pintae_publication_immutable()"
    )
    for table in GUARDED:
        op.execute(
            f"CREATE TRIGGER {table}_no_truncate BEFORE TRUNCATE ON {table} "
            "FOR EACH STATEMENT EXECUTE FUNCTION pintae_reference_no_truncate()"
        )
    tables = ", ".join(GUARDED)
    op.execute(f"REVOKE UPDATE, DELETE, TRUNCATE ON {tables} FROM PUBLIC, pintae_app, CURRENT_USER")
    for table in PARENTS:
        op.execute(f"GRANT UPDATE (status) ON {table} TO CURRENT_USER")


def downgrade() -> None:
    tables = ", ".join(GUARDED)
    for table in PARENTS:
        op.execute(f"REVOKE UPDATE (status) ON {table} FROM CURRENT_USER")
    op.execute(f"GRANT UPDATE, DELETE, TRUNCATE ON {tables} TO CURRENT_USER")
    for table in GUARDED:
        op.execute(f"DROP TRIGGER IF EXISTS {table}_no_truncate ON {table}")
    op.execute("DROP TRIGGER IF EXISTS publications_immutable ON publications")
    op.execute("DROP FUNCTION IF EXISTS pintae_publication_immutable()")
    op.execute("DROP FUNCTION IF EXISTS pintae_reference_no_truncate()")
    op.execute(OLD_CHILD_FUNC)
    op.execute(OLD_PARENT_FUNC)
    op.drop_column("calendar_versions", "content")
