"""B2: sign-in (password plus TOTP, invitations, recovery codes, password reset), session
stages, sign-in throttle and generated files (TRD 8.1, schema.md).

Revision ID: 0005
Revises: 0004b
Create Date: 2026-11-11
"""

from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0005"
down_revision = "0004b"
branch_labels = None
depends_on = None

APP_ROLE = "pintae_app"
NEW_TENANT = ("invites", "recovery_codes", "password_resets", "files")


def _tenant_cols(table: str) -> list[Any]:
    return [
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("firm_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(["firm_id"], ["firms.id"], name=op.f(f"fk_{table}_firm_id_firms")),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{table}")),
    ]


FUNCS = r"""
DROP FUNCTION pintae_resolve_session(bytea);
-- Session lookup before a firm is known. 30 minutes idle, absolute expiry, user enabled.
CREATE FUNCTION pintae_resolve_session(p_token_hash bytea)
RETURNS TABLE (session_id uuid, user_id uuid, firm_id uuid, role text, stage text)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $f$
BEGIN
  RETURN QUERY
  UPDATE sessions s SET last_seen_at = now()
    FROM users u
   WHERE s.token_hash = p_token_hash AND u.id = s.user_id
     AND s.ended_at IS NULL AND u.disabled_at IS NULL
     AND s.absolute_expires_at > now() AND s.last_seen_at > now() - interval '30 minutes'
  RETURNING s.id, s.user_id, s.firm_id, u.role, s.stage;
END $f$;

-- Password step of sign-in: the e-mail address is the only global key (users.email unique).
CREATE FUNCTION pintae_login_lookup(p_email text)
RETURNS TABLE (user_id uuid, firm_id uuid, password_hash text, disabled boolean)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $f$
  SELECT u.id, u.firm_id, u.password_hash, u.disabled_at IS NOT NULL
    FROM users u WHERE u.email = p_email::citext
$f$;

-- Which firm a single-use token belongs to; the caller then works inside that firm's
-- tenancy session, where expiry and use are checked under row-level security.
CREATE FUNCTION pintae_token_firm(p_kind text, p_token_hash bytea) RETURNS uuid
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $f$
BEGIN
  IF p_kind = 'invite' THEN
    RETURN (SELECT i.firm_id FROM invites i WHERE i.token_hash = p_token_hash);
  ELSIF p_kind = 'password_reset' THEN
    RETURN (SELECT r.firm_id FROM password_resets r WHERE r.token_hash = p_token_hash);
  END IF;
  RETURN NULL;
END $f$;

REVOKE ALL ON FUNCTION pintae_resolve_session(bytea), pintae_login_lookup(text),
  pintae_token_firm(text, bytea) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION pintae_resolve_session(bytea), pintae_login_lookup(text),
  pintae_token_firm(text, bytea) TO pintae_app;
"""

OLD_RESOLVE = r"""
DROP FUNCTION pintae_resolve_session(bytea);
CREATE FUNCTION pintae_resolve_session(p_token_hash bytea)
RETURNS TABLE (session_id uuid, user_id uuid, firm_id uuid, role text)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $f$
BEGIN
  RETURN QUERY
  UPDATE sessions s SET last_seen_at = now()
    FROM users u
   WHERE s.token_hash = p_token_hash AND u.id = s.user_id
     AND s.ended_at IS NULL AND u.disabled_at IS NULL
     AND s.absolute_expires_at > now() AND s.last_seen_at > now() - interval '30 minutes'
  RETURNING s.id, s.user_id, s.firm_id, u.role;
END $f$;
REVOKE ALL ON FUNCTION pintae_resolve_session(bytea) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION pintae_resolve_session(bytea) TO pintae_app;
"""


def upgrade() -> None:
    op.add_column("users", sa.Column("totp_confirmed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("totp_last_step", sa.BigInteger(), nullable=True))
    # Sessions created before B2 get the least stage, so they cannot reach application routes.
    op.add_column(
        "sessions",
        sa.Column("stage", sa.Text(), server_default=sa.text("'password'"), nullable=False),
    )
    op.alter_column("sessions", "stage", server_default=None)
    op.add_column(
        "sessions",
        sa.Column("failed_codes", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )
    op.create_check_constraint(
        op.f("ck_sessions_stage"), "sessions", "stage IN ('password', 'enrol', 'full')"
    )
    op.create_table(
        "invites",
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("email", postgresql.CITEXT(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("token_hash", sa.LargeBinary(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        *_tenant_cols("invites"),
        sa.CheckConstraint(
            "role IN ('owner', 'reviewer', 'preparer')", name=op.f("ck_invites_role")
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name=op.f("fk_invites_created_by_users")
        ),
        sa.UniqueConstraint("token_hash", name=op.f("uq_invites_token_hash")),
    )
    op.create_table(
        "recovery_codes",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("code_hash", sa.Text(), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        *_tenant_cols("recovery_codes"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_recovery_codes_user_id_users"),
            ondelete="CASCADE",
        ),
    )
    op.create_table(
        "password_resets",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("token_hash", sa.LargeBinary(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        *_tenant_cols("password_resets"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_password_resets_user_id_users")
        ),
        sa.UniqueConstraint("token_hash", name=op.f("uq_password_resets_token_hash")),
    )
    op.create_table(
        "files",
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("entity_id", sa.UUID(), nullable=True),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("sha256", sa.LargeBinary(), nullable=False),
        sa.Column("content_type", sa.Text(), nullable=False),
        sa.Column("download_name", sa.Text(), nullable=False),
        sa.Column("byte_size", sa.BigInteger(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        *_tenant_cols("files"),
        sa.CheckConstraint(
            "purpose IN ('report', 'fix_list', 'handoff', 'export', 'dashboard_export')",
            name=op.f("ck_files_purpose"),
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name=op.f("fk_files_created_by_users")),
        sa.ForeignKeyConstraint(
            ["entity_id"], ["client_entities.id"], name=op.f("fk_files_entity_id_client_entities")
        ),
        sa.UniqueConstraint("storage_key", name=op.f("uq_files_storage_key")),
    )
    op.create_table(
        "auth_attempts",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("key_hash", sa.LargeBinary(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("succeeded", sa.Boolean(), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("kind IN ('account', 'client')", name=op.f("ck_auth_attempts_kind")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_auth_attempts")),
    )
    op.create_index("ix_auth_attempts_key_at", "auth_attempts", ["key_hash", "at"])
    for table in NEW_TENANT:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table} "
            "USING (firm_id = pintae_current_firm()) WITH CHECK (firm_id = pintae_current_firm())"
        )
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT ON auth_attempts TO {APP_ROLE}")
    op.execute(FUNCS)


def downgrade() -> None:
    op.execute(OLD_RESOLVE)
    op.execute("DROP FUNCTION IF EXISTS pintae_login_lookup(text)")
    op.execute("DROP FUNCTION IF EXISTS pintae_token_firm(text, bytea)")
    op.drop_index("ix_auth_attempts_key_at", table_name="auth_attempts")
    op.drop_table("auth_attempts")
    for table in ("files", "password_resets", "recovery_codes", "invites"):
        op.drop_table(table)
    op.drop_constraint(op.f("ck_sessions_stage"), "sessions", type_="check")
    op.drop_column("sessions", "failed_codes")
    op.drop_column("sessions", "stage")
    op.drop_column("users", "totp_last_step")
    op.drop_column("users", "totp_confirmed_at")
