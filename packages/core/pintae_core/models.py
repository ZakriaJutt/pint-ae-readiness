"""ORM models for the B1 tables of schema.md. Constraints and indexes are declared here and
in the migration; ``scripts/check_schema_parity.py`` compares the two (R-08, IT-11).

Row-level security, grants, triggers and security-definer functions live in the migration
only (they are not expressible as SQLAlchemy metadata); the parity check compares tables,
columns, constraints and indexes.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    MetaData,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, CITEXT, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NAMING = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


# The migration head this code expects; /readyz compares it with alembic_version.
SCHEMA_REVISION = "0006"


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING)
    type_annotation_map = {  # noqa: RUF012 - SQLAlchemy declarative hook
        dict[str, Any]: JSONB,
        uuid.UUID: UUID(as_uuid=True),
        datetime: DateTime(timezone=True),
        date: Date,
        bytes: LargeBinary,
        str: Text,
    }


def _pk() -> Mapped[uuid.UUID]:
    return mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))


def _created() -> Mapped[datetime]:
    return mapped_column(server_default=text("now()"))


def _in(col: str, values: tuple[str, ...]) -> str:
    return f"{col} IN ({', '.join(repr(v) for v in values)})"


# Tables whose rows belong to one firm and sit under row-level security.
TENANT_TABLES = (
    "firms",
    "users",
    "sessions",
    "invites",
    "recovery_codes",
    "password_resets",
    "files",
    "client_entities",
    "segment_assessments",
    "uploads",
    "staged_rows",
    "column_mappings",
    "value_mappings",
    "check_runs",
    "findings",
    "finding_exceptions",
    "readiness_snapshots",
    "asp_statuses",
    "reports",
    "jobs",
    "idempotency_keys",
    "audit_events",
)
GLOBAL_TABLES = (
    "vendor_users",
    "calendar_versions",
    "calendar_rules",
    "provisions",
    "rule_packs",
    "rules",
    "publications",
    "system_flags",
    "worker_heartbeats",
    "auth_attempts",
)


class TenantMixin:
    id: Mapped[uuid.UUID] = _pk()
    firm_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("firms.id"))
    created_at: Mapped[datetime] = _created()


# ----------------------------------------------------------------------------- global


class VendorUser(Base):
    __tablename__ = "vendor_users"
    id: Mapped[uuid.UUID] = _pk()
    created_at: Mapped[datetime] = _created()
    email: Mapped[str] = mapped_column(CITEXT, unique=True)
    role: Mapped[str]
    password_hash: Mapped[str]
    totp_secret_enc: Mapped[bytes]
    disabled_at: Mapped[datetime | None]
    __table_args__ = (CheckConstraint(_in("role", ("publisher", "support")), name="role"),)


class CalendarVersion(Base):
    __tablename__ = "calendar_versions"
    id: Mapped[uuid.UUID] = _pk()
    created_at: Mapped[datetime] = _created()
    code: Mapped[str] = mapped_column(unique=True)
    basis: Mapped[str]
    source_refs: Mapped[dict[str, Any]]
    effective_from: Mapped[date | None]
    effective_label: Mapped[str]
    status: Mapped[str]
    content_hash: Mapped[bytes]
    published_at: Mapped[datetime | None]
    # The calendar file as published; loaders verify it against content_hash (B1-012).
    content: Mapped[dict[str, Any] | None]
    # B1-014: publication, derived_from_rows (backfilled once by migration 0004b) or
    # legacy_unverified (no content; never newly pinned; pinned results read Stale).
    content_origin: Mapped[str | None]
    __table_args__ = (
        CheckConstraint(_in("effective_label", ("stated", "assumed")), name="effective_label"),
        CheckConstraint(_in("status", ("draft", "published", "withdrawn")), name="status"),
        CheckConstraint(
            _in("content_origin", ("publication", "derived_from_rows", "legacy_unverified")),
            name="content_origin",
        ),
    )


class CalendarRuleRow(Base):
    __tablename__ = "calendar_rules"
    id: Mapped[uuid.UUID] = _pk()
    calendar_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("calendar_versions.id"))
    segment: Mapped[str]
    deadline_basis: Mapped[str]
    appoint_by: Mapped[date | None]
    implement_by: Mapped[date | None]
    candidate_segments: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    source_refs: Mapped[dict[str, Any]]
    note: Mapped[str | None]
    discrepancy: Mapped[str | None]
    __table_args__ = (
        UniqueConstraint("calendar_version_id", "segment"),
        CheckConstraint(
            _in(
                "deadline_basis",
                ("fixed_date", "before_first_invoice", "not_subject", "earliest_of_candidates"),
            ),
            name="deadline_basis",
        ),
    )


class ProvisionRow(Base):
    __tablename__ = "provisions"
    id: Mapped[uuid.UUID] = _pk()
    calendar_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("calendar_versions.id"))
    code: Mapped[str]
    kind: Mapped[str]
    applies_from: Mapped[date | None]
    applies_to: Mapped[date | None]
    selector: Mapped[dict[str, Any]]
    effect: Mapped[str]
    rule_code: Mapped[str | None]
    source_refs: Mapped[dict[str, Any]]
    __table_args__ = (
        UniqueConstraint("calendar_version_id", "code"),
        CheckConstraint(
            _in(
                "kind", ("grace_period", "voluntary_phase", "pending_requirement", "residual_scope")
            ),
            name="kind",
        ),
        CheckConstraint(
            _in("effect", ("exclude_from_denominator", "note_only", "activate_rule")), name="effect"
        ),
    )


class RulePackRow(Base):
    __tablename__ = "rule_packs"
    id: Mapped[uuid.UUID] = _pk()
    created_at: Mapped[datetime] = _created()
    code: Mapped[str] = mapped_column(unique=True)
    basis: Mapped[str]
    released_on: Mapped[date]
    effective_from: Mapped[date | None]
    effective_label: Mapped[str]
    status: Mapped[str]
    content_hash: Mapped[bytes]
    published_at: Mapped[datetime | None]
    # The full pack file as published (code lists, shapes, patterns). Immutable.
    content: Mapped[dict[str, Any]]
    __table_args__ = (
        CheckConstraint(_in("effective_label", ("stated", "assumed")), name="effective_label"),
        CheckConstraint(_in("status", ("draft", "published", "withdrawn")), name="status"),
    )


class RuleRow(Base):
    __tablename__ = "rules"
    id: Mapped[uuid.UUID] = _pk()
    rule_pack_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("rule_packs.id"))
    code: Mapped[str]
    severity: Mapped[str]
    applies_to: Mapped[dict[str, Any]]
    valid_from: Mapped[date | None]
    valid_to: Mapped[date | None]
    source_refs: Mapped[dict[str, Any]]
    description: Mapped[str]
    __table_args__ = (
        UniqueConstraint("rule_pack_id", "code"),
        CheckConstraint(_in("severity", ("blocker", "warning")), name="severity"),
    )


class Publication(Base):
    __tablename__ = "publications"
    id: Mapped[uuid.UUID] = _pk()
    created_at: Mapped[datetime] = _created()
    object_type: Mapped[str]
    object_id: Mapped[uuid.UUID]
    content_hash: Mapped[bytes]
    fixture_run_ref: Mapped[str]
    fixture_hash: Mapped[bytes]
    confirmed_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("vendor_users.id"))
    confirmed_at: Mapped[datetime]
    __table_args__ = (
        CheckConstraint(_in("object_type", ("rule_pack", "calendar_version")), name="object_type"),
        CheckConstraint("fixture_hash = content_hash", name="fixture_hash_matches"),
    )


class SystemFlag(Base):
    __tablename__ = "system_flags"
    key: Mapped[str] = mapped_column(primary_key=True)
    value: Mapped[bool]
    reason: Mapped[str | None]
    set_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("vendor_users.id"))
    set_at: Mapped[datetime]


class AuthAttempt(Base):
    """Sign-in throttle (ASVS 6.3.1). Keys are hashes of an e-mail address or a client
    address, never the value itself. Global: attempts happen before a firm is known."""

    __tablename__ = "auth_attempts"
    id: Mapped[uuid.UUID] = _pk()
    key_hash: Mapped[bytes]
    kind: Mapped[str]
    succeeded: Mapped[bool]
    at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    __table_args__ = (
        CheckConstraint(_in("kind", ("account", "client")), name="kind"),
        Index("ix_auth_attempts_key_at", "key_hash", "at"),
    )


class WorkerHeartbeat(Base):
    """Readiness signal for OPS-04 (not in schema.md before B1; added there)."""

    __tablename__ = "worker_heartbeats"
    worker_id: Mapped[str] = mapped_column(primary_key=True)
    seen_at: Mapped[datetime]


# ----------------------------------------------------------------------------- tenant


class Firm(Base):
    __tablename__ = "firms"
    id: Mapped[uuid.UUID] = _pk()
    created_at: Mapped[datetime] = _created()
    legal_name: Mapped[str]
    plan: Mapped[str] = mapped_column(server_default=text("'pilot'"))
    plan_limit: Mapped[int] = mapped_column(Integer, server_default=text("30"))
    deleted_at: Mapped[datetime | None]
    __table_args__ = (
        CheckConstraint(_in("plan", ("pilot", "starter", "pro", "business")), name="plan"),
    )


class User(TenantMixin, Base):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(CITEXT, unique=True)
    role: Mapped[str]
    password_hash: Mapped[str]
    totp_secret_enc: Mapped[bytes]
    disabled_at: Mapped[datetime | None]
    totp_confirmed_at: Mapped[datetime | None]  # B2: enrolment completed with a valid code
    totp_last_step: Mapped[int | None] = mapped_column(BigInteger)  # B2: replay guard
    __table_args__ = (CheckConstraint(_in("role", ("owner", "reviewer", "preparer")), name="role"),)


class SessionRow(TenantMixin, Base):
    __tablename__ = "sessions"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    token_hash: Mapped[bytes] = mapped_column(unique=True)
    last_seen_at: Mapped[datetime]
    absolute_expires_at: Mapped[datetime]
    ended_at: Mapped[datetime | None]
    # B2: 'password' (TOTP pending), 'enrol' (TOTP enrolment pending) or 'full'. Only a
    # 'full' session reaches the application routes.
    stage: Mapped[str]
    failed_codes: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    __table_args__ = (CheckConstraint(_in("stage", ("password", "enrol", "full")), name="stage"),)


class Invite(TenantMixin, Base):
    __tablename__ = "invites"
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    email: Mapped[str] = mapped_column(CITEXT)
    role: Mapped[str]
    token_hash: Mapped[bytes] = mapped_column(unique=True)
    expires_at: Mapped[datetime]
    used_at: Mapped[datetime | None]
    revoked_at: Mapped[datetime | None]
    __table_args__ = (CheckConstraint(_in("role", ("owner", "reviewer", "preparer")), name="role"),)


class RecoveryCode(TenantMixin, Base):
    __tablename__ = "recovery_codes"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    code_hash: Mapped[str]
    used_at: Mapped[datetime | None]


class PasswordReset(TenantMixin, Base):
    __tablename__ = "password_resets"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    token_hash: Mapped[bytes] = mapped_column(unique=True)
    expires_at: Mapped[datetime]
    used_at: Mapped[datetime | None]


class FileRow(TenantMixin, Base):
    """Generated files (fix lists, reports, exports). Served only through GET /files/{id}."""

    __tablename__ = "files"
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    purpose: Mapped[str]
    entity_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("client_entities.id"))
    storage_key: Mapped[str] = mapped_column(unique=True)
    sha256: Mapped[bytes]
    content_type: Mapped[str]
    download_name: Mapped[str]
    byte_size: Mapped[int] = mapped_column(BigInteger)
    expires_at: Mapped[datetime | None]
    __table_args__ = (
        CheckConstraint(
            _in("purpose", ("report", "fix_list", "handoff", "export", "dashboard_export")),
            name="purpose",
        ),
    )


class ClientEntity(TenantMixin, Base):
    __tablename__ = "client_entities"
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    legal_name: Mapped[str]
    registration_type: Mapped[str] = mapped_column(server_default=text("'unknown'"))
    licence_number: Mapped[str | None]
    licence_authority: Mapped[str | None]
    passport_country: Mapped[str | None]
    address_line: Mapped[str | None]
    city: Mapped[str | None]
    emirate_code: Mapped[str | None]
    country_code: Mapped[str | None]
    vat_registered: Mapped[str] = mapped_column(server_default=text("'unknown'"))
    trn: Mapped[str | None]
    tin: Mapped[str | None]
    source_ledger: Mapped[str]
    current_segment_assessment_id: Mapped[uuid.UUID | None]
    profile_version: Mapped[int] = mapped_column(Integer, server_default=text("1"))
    deleted_at: Mapped[datetime | None]
    __table_args__ = (
        CheckConstraint(
            _in("registration_type", ("TL", "EID", "PAS", "CD", "unknown")),
            name="registration_type",
        ),
        CheckConstraint(
            "emirate_code IS NULL OR "
            + _in("emirate_code", ("AUH", "DXB", "SHJ", "UAQ", "FUJ", "AJM", "RAK")),
            name="emirate_code",
        ),
        CheckConstraint(_in("vat_registered", ("yes", "no", "unknown")), name="vat_registered"),
        CheckConstraint("trn IS NULL OR trn ~ '^[0-9]{15}$'", name="trn"),
        CheckConstraint("tin IS NULL OR tin ~ '^[0-9]{10}$'", name="tin"),
        Index(
            "uq_client_entities_firm_trn",
            "firm_id",
            "trn",
            unique=True,
            postgresql_where=text("trn IS NOT NULL AND deleted_at IS NULL"),
        ),
        Index("ix_client_entities_firm_deleted", "firm_id", "deleted_at"),
    )


class SegmentAssessment(TenantMixin, Base):
    __tablename__ = "segment_assessments"
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    entity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("client_entities.id"))
    version: Mapped[int] = mapped_column(Integer)
    entity_type: Mapped[str]
    newly_established: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    first_invoice_state: Mapped[str | None]
    first_invoice_on: Mapped[date | None]
    b2c_only: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    revenue_band: Mapped[str]
    period_end: Mapped[date | None]
    evidence_type: Mapped[str | None]
    segment: Mapped[str]
    state: Mapped[str]
    decided_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    decided_at: Mapped[datetime | None]
    note: Mapped[str | None]
    __table_args__ = (
        UniqueConstraint("entity_id", "version"),
        CheckConstraint(_in("entity_type", ("person", "government_entity")), name="entity_type"),
        CheckConstraint(
            "first_invoice_state IS NULL OR "
            + _in("first_invoice_state", ("issued", "not_yet", "unknown")),
            name="first_invoice_state",
        ),
        CheckConstraint(
            _in("revenue_band", ("ge_50m", "eq_50m", "lt_50m", "unknown")), name="revenue_band"
        ),
        CheckConstraint(
            "evidence_type IS NULL OR "
            + _in(
                "evidence_type", ("financial_statements", "other_documentation", "client_statement")
            ),
            name="evidence_type",
        ),
        CheckConstraint(
            _in("segment", ("SEG-L", "SEG-S", "SEG-G", "SEG-N", "SEG-X", "SEG-U")), name="segment"
        ),
        CheckConstraint(_in("state", ("proposed", "approved", "returned")), name="state"),
        Index("ix_segment_assessments_entity_version", "entity_id", text("version DESC")),
    )


class Upload(TenantMixin, Base):
    __tablename__ = "uploads"
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    entity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("client_entities.id"))
    dataset: Mapped[str]
    sha256: Mapped[bytes]
    storage_key: Mapped[str] = mapped_column(unique=True)
    original_name: Mapped[str]
    byte_size: Mapped[int] = mapped_column(BigInteger)
    row_count: Mapped[int | None] = mapped_column(Integer)
    header_fingerprint: Mapped[bytes | None]
    state: Mapped[str]
    reject_reason: Mapped[str | None]
    expires_at: Mapped[datetime | None]
    __table_args__ = (
        UniqueConstraint("firm_id", "entity_id", "dataset", "sha256"),
        CheckConstraint(_in("dataset", ("customers", "items", "invoices")), name="dataset"),
        CheckConstraint(_in("state", ("received", "parsed", "rejected", "removed")), name="state"),
        Index("ix_uploads_latest", "firm_id", "entity_id", "dataset", text("created_at DESC")),
        Index("ix_uploads_expires_at", "expires_at"),
    )


class StagedRow(TenantMixin, Base):
    __tablename__ = "staged_rows"
    upload_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("uploads.id", ondelete="CASCADE"))
    sheet: Mapped[str | None]
    row_number: Mapped[int] = mapped_column(Integer)
    cells: Mapped[dict[str, Any]]
    record_key: Mapped[str | None]
    __table_args__ = (
        Index(
            "uq_staged_rows_upload_sheet_row",
            "upload_id",
            text("coalesce(sheet, '')"),
            "row_number",
            unique=True,
        ),
    )


class ColumnMapping(TenantMixin, Base):
    __tablename__ = "column_mappings"
    upload_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("uploads.id"))
    version: Mapped[int] = mapped_column(Integer)
    header_fingerprint: Mapped[bytes]
    mapping: Mapped[dict[str, Any]]
    suggested_by: Mapped[str] = mapped_column(server_default=text("'dictionary'"))
    state: Mapped[str]
    confirmed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    confirmed_at: Mapped[datetime | None]
    approved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[datetime | None]
    __table_args__ = (
        UniqueConstraint("upload_id", "version"),
        CheckConstraint(
            _in("state", ("draft", "confirmed", "approved", "returned", "replaced")), name="state"
        ),
        Index(
            "ix_column_mappings_reuse",
            "firm_id",
            "header_fingerprint",
            postgresql_where=text("state = 'confirmed'"),
        ),
    )


class ValueMapping(TenantMixin, Base):
    __tablename__ = "value_mappings"
    entity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("client_entities.id"))
    kind: Mapped[str]
    source_value: Mapped[str]
    target_code: Mapped[str | None]
    state: Mapped[str]
    approved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    __table_args__ = (
        UniqueConstraint("entity_id", "kind", "source_value"),
        CheckConstraint(
            _in(
                "kind",
                ("unit", "emirate", "tax_treatment", "document_type", "buyer_class", "country"),
            ),
            name="kind",
        ),
        CheckConstraint(_in("state", ("suggested", "confirmed", "approved")), name="state"),
    )


class CheckRun(TenantMixin, Base):
    __tablename__ = "check_runs"
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    entity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("client_entities.id"))
    rule_pack_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("rule_packs.id"))
    segment_assessment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("segment_assessments.id"))
    profile_version: Mapped[int] = mapped_column(Integer)
    inputs: Mapped[dict[str, Any]]
    input_hash: Mapped[bytes]
    newest_data_on: Mapped[date]
    state: Mapped[str]
    result_hash: Mapped[bytes | None]
    finished_at: Mapped[datetime | None]
    __table_args__ = (
        UniqueConstraint("entity_id", "input_hash"),
        CheckConstraint(_in("state", ("queued", "running", "succeeded", "failed")), name="state"),
        Index("ix_check_runs_staleness", "entity_id", "rule_pack_id", "newest_data_on"),
    )


class FindingRow(TenantMixin, Base):
    __tablename__ = "findings"
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("check_runs.id", ondelete="CASCADE"))
    entity_id: Mapped[uuid.UUID]
    rule_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("rules.id"))
    dataset: Mapped[str]
    record_key: Mapped[str]
    upload_id: Mapped[uuid.UUID | None]
    sheet: Mapped[str | None]
    row_number: Mapped[int] = mapped_column(Integer)
    column_name: Mapped[str | None]
    value_found: Mapped[str | None]
    outcome: Mapped[str]
    review_resolution: Mapped[str | None]
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    resolved_at: Mapped[datetime | None]
    not_checked_reason: Mapped[str | None]
    message: Mapped[str | None]  # what is wrong and what a valid value looks like
    asp_also_flagged: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    fingerprint: Mapped[bytes]
    __table_args__ = (
        UniqueConstraint("run_id", "fingerprint"),
        CheckConstraint(
            _in(
                "outcome", ("fail", "not_checked", "manual_review", "out_of_scope", "grace_period")
            ),
            name="outcome",
        ),
        CheckConstraint(
            "review_resolution IS NULL OR "
            + _in("review_resolution", ("confirmed_self_billed", "type_corrected")),
            name="review_resolution",
        ),
        CheckConstraint(
            "not_checked_reason IS NULL OR "
            + _in(
                "not_checked_reason",
                (
                    "field_absent",
                    "column_unmapped",
                    "value_unmapped",
                    "profile_unknown",
                    "prerequisite_unresolved",
                ),
            ),
            name="not_checked_reason",
        ),
        CheckConstraint(
            "(outcome = 'not_checked') = (not_checked_reason IS NOT NULL)",
            name="not_checked_has_reason",
        ),
        Index("ix_findings_fix_list", "entity_id", "run_id", "rule_id", "outcome"),
        Index("ix_findings_entity_fingerprint", "entity_id", "fingerprint"),
    )


class FindingException(TenantMixin, Base):
    __tablename__ = "finding_exceptions"
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    entity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("client_entities.id"))
    fingerprint: Mapped[bytes]
    reason: Mapped[str]
    state: Mapped[str]
    decided_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    decided_at: Mapped[datetime | None]
    rule_pack_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("rule_packs.id"))
    __table_args__ = (
        CheckConstraint(
            _in("state", ("proposed", "accepted", "rejected", "withdrawn")), name="state"
        ),
        Index(
            "uq_finding_exceptions_open",
            "entity_id",
            "fingerprint",
            "rule_pack_id",
            unique=True,
            postgresql_where=text("state IN ('proposed', 'accepted')"),
        ),
    )


class ReadinessSnapshot(TenantMixin, Base):
    __tablename__ = "readiness_snapshots"
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("check_runs.id"), unique=True)
    entity_id: Mapped[uuid.UUID]
    base_status: Mapped[str]
    score_by_dataset: Mapped[dict[str, Any]]
    failed_blockers: Mapped[int] = mapped_column(Integer)
    unchecked_blockers: Mapped[int] = mapped_column(Integer)
    unresolved_manual_reviews: Mapped[int] = mapped_column(Integer)
    not_assessed_self_billed: Mapped[int] = mapped_column(Integer)
    accepted_exceptions: Mapped[int] = mapped_column(Integer)
    # Required datasets mapped with no data rows (B1-002); Data-ready requires 0.
    empty_datasets: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    mappings_approved: Mapped[bool]
    is_current: Mapped[bool]
    __table_args__ = (
        CheckConstraint(
            "base_status <> 'data_ready' OR (failed_blockers = 0 AND unchecked_blockers = 0 "
            "AND unresolved_manual_reviews = 0 AND accepted_exceptions = 0 "
            "AND empty_datasets = 0 AND mappings_approved)",
            name="data_ready_requires_clean",
        ),
        CheckConstraint(
            _in(
                "base_status",
                (
                    "not_started",
                    "segment_not_confirmed",
                    "data_incomplete",
                    "gaps_open",
                    "checks_incomplete",
                    "exceptions_open",
                    "review_pending",
                    "data_ready",
                ),
            ),
            name="base_status",
        ),
        Index(
            "uq_readiness_snapshots_current",
            "entity_id",
            unique=True,
            postgresql_where=text("is_current"),
        ),
        Index(
            "ix_readiness_snapshots_status",
            "firm_id",
            "base_status",
            postgresql_where=text("is_current"),
        ),
    )


class AspStatus(TenantMixin, Base):
    __tablename__ = "asp_statuses"
    entity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("client_entities.id"))
    status: Mapped[str]
    asp_name: Mapped[str | None]
    appointed_on: Mapped[date | None]
    emaratax_done: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    go_live_on: Mapped[date | None]
    note: Mapped[str | None]
    is_current: Mapped[bool]
    __table_args__ = (
        CheckConstraint(
            _in("status", ("not_appointed", "appointed", "onboarded", "live")), name="status"
        ),
        Index("ix_asp_statuses_current", "firm_id", "status", postgresql_where=text("is_current")),
        Index(
            "uq_asp_statuses_one_current",
            "entity_id",
            unique=True,
            postgresql_where=text("is_current"),
        ),
    )


class Report(TenantMixin, Base):
    __tablename__ = "reports"
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    entity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("client_entities.id"))
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("check_runs.id"))
    reference_code: Mapped[str] = mapped_column(unique=True)
    state: Mapped[str]
    pins: Mapped[dict[str, Any]]
    printed_status: Mapped[str | None]
    approved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[datetime | None]
    delivered_at: Mapped[datetime | None]
    reissue_noted_at: Mapped[datetime | None]
    content_hash: Mapped[bytes | None]
    __table_args__ = (
        CheckConstraint(_in("state", ("draft", "approved")), name="state"),
        Index("ix_reports_firm_reference", "firm_id", "reference_code"),
    )


class Job(TenantMixin, Base):
    __tablename__ = "jobs"
    kind: Mapped[str]
    payload: Mapped[dict[str, Any]]
    state: Mapped[str]
    state_version: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    attempt_id: Mapped[uuid.UUID | None]
    attempts: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    lease_expires_at: Mapped[datetime | None]
    run_after: Mapped[datetime] = mapped_column(server_default=text("now()"))
    correlation_id: Mapped[uuid.UUID]
    last_error_code: Mapped[str | None]
    __table_args__ = (
        CheckConstraint(
            _in("state", ("queued", "running", "succeeded", "failed", "cancelled")), name="state"
        ),
        Index("ix_jobs_claim", "state", "run_after", postgresql_where=text("state = 'queued'")),
        Index("ix_jobs_lease", "lease_expires_at", postgresql_where=text("state = 'running'")),
    )


class IdempotencyKey(TenantMixin, Base):
    __tablename__ = "idempotency_keys"
    key: Mapped[str]
    route: Mapped[str]
    request_hash: Mapped[bytes]
    response: Mapped[dict[str, Any]]
    expires_at: Mapped[datetime]
    __table_args__ = (UniqueConstraint("firm_id", "route", "key"),)


class AuditEvent(TenantMixin, Base):
    __tablename__ = "audit_events"
    actor_id: Mapped[uuid.UUID | None]
    actor_kind: Mapped[str]
    action: Mapped[str]
    object_type: Mapped[str]
    object_id: Mapped[uuid.UUID | None]
    detail: Mapped[dict[str, Any]]
    correlation_id: Mapped[uuid.UUID]
    __table_args__ = (
        CheckConstraint(_in("actor_kind", ("user", "vendor", "system")), name="actor_kind"),
        Index("ix_audit_events_firm_created", "firm_id", text("created_at DESC")),
        Index("ix_audit_events_object", "firm_id", "object_type", "object_id"),
    )
