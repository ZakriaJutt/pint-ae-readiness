"""B1 review round 1: empty-dataset guard on snapshots (B1-002), country value mappings
(B1-003), the exactly-AED-50M band, and least privilege on vendor credentials.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-11
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

OLD_CLEAN = (
    "base_status <> 'data_ready' OR (failed_blockers = 0 AND unchecked_blockers = 0 "
    "AND unresolved_manual_reviews = 0 AND accepted_exceptions = 0 AND mappings_approved)"
)
NEW_CLEAN = (
    "base_status <> 'data_ready' OR (failed_blockers = 0 AND unchecked_blockers = 0 "
    "AND unresolved_manual_reviews = 0 AND accepted_exceptions = 0 "
    "AND empty_datasets = 0 AND mappings_approved)"
)


def upgrade() -> None:
    # Small table, constant default: added NOT NULL directly (no backfill job needed).
    op.add_column(
        "readiness_snapshots",
        sa.Column("empty_datasets", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )
    op.drop_constraint(
        op.f("ck_readiness_snapshots_data_ready_requires_clean"),
        "readiness_snapshots",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_readiness_snapshots_data_ready_requires_clean"), "readiness_snapshots", NEW_CLEAN
    )
    op.drop_constraint(op.f("ck_value_mappings_kind"), "value_mappings", type_="check")
    op.create_check_constraint(
        op.f("ck_value_mappings_kind"),
        "value_mappings",
        "kind IN ('unit', 'emirate', 'tax_treatment', 'document_type', 'buyer_class', 'country')",
    )
    op.drop_constraint(
        op.f("ck_segment_assessments_revenue_band"), "segment_assessments", type_="check"
    )
    op.create_check_constraint(
        op.f("ck_segment_assessments_revenue_band"),
        "segment_assessments",
        "revenue_band IN ('ge_50m', 'eq_50m', 'lt_50m', 'unknown')",
    )
    # The application role never reads vendor credentials (ASVS 5.0 V8).
    op.execute("REVOKE SELECT ON vendor_users FROM pintae_app")


def downgrade() -> None:
    op.execute("GRANT SELECT ON vendor_users TO pintae_app")
    op.drop_constraint(
        op.f("ck_segment_assessments_revenue_band"), "segment_assessments", type_="check"
    )
    op.create_check_constraint(
        op.f("ck_segment_assessments_revenue_band"),
        "segment_assessments",
        "revenue_band IN ('ge_50m', 'lt_50m', 'unknown')",
    )
    op.drop_constraint(op.f("ck_value_mappings_kind"), "value_mappings", type_="check")
    op.create_check_constraint(
        op.f("ck_value_mappings_kind"),
        "value_mappings",
        "kind IN ('unit', 'emirate', 'tax_treatment', 'document_type', 'buyer_class')",
    )
    op.drop_constraint(
        op.f("ck_readiness_snapshots_data_ready_requires_clean"),
        "readiness_snapshots",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_readiness_snapshots_data_ready_requires_clean"), "readiness_snapshots", OLD_CLEAN
    )
    op.drop_column("readiness_snapshots", "empty_datasets")
