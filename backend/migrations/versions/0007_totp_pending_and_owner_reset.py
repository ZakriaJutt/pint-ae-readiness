"""B2-001: a new TOTP secret is held as pending until it is confirmed, so the confirmed
factor is never cleared by starting a re-enrolment; Owner-issued re-enrolment invitations
name the existing user.

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-11
"""

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("totp_pending_secret_enc", sa.LargeBinary(), nullable=True))
    op.add_column("invites", sa.Column("user_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        op.f("fk_invites_user_id_users"), "invites", "users", ["user_id"], ["id"]
    )


def downgrade() -> None:
    op.drop_constraint(op.f("fk_invites_user_id_users"), "invites", type_="foreignkey")
    op.drop_column("invites", "user_id")
    op.drop_column("users", "totp_pending_secret_enc")
