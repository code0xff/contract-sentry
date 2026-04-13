"""Initial schema — all domain tables.

Revision ID: 0001
Revises:
Create Date: 2026-04-13
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

# --------------------------------------------------------------------------- #
# Enum values (mirrors app/schemas/enums.py)
# --------------------------------------------------------------------------- #
_contract_language = sa.Enum(
    "solidity", "vyper", "bytecode",
    name="contractlanguage",
)
_job_status = sa.Enum(
    "pending", "running", "completed", "failed", "cancelled",
    name="jobstatus",
)
_severity = sa.Enum(
    "critical", "high", "medium", "low", "info",
    name="severity",
)
_vulnerability_type = sa.Enum(
    "reentrancy", "integer_overflow", "access_control", "unchecked_return",
    "timestamp_dependency", "delegatecall", "self_destruct", "front_running",
    "denial_of_service", "flash_loan", "other",
    name="vulnerabilitytype",
)
_tool_name = sa.Enum(
    "slither", "mythril", "echidna", "foundry", "internal",
    name="toolname",
)
_simulation_status = sa.Enum(
    "queued", "running", "succeeded", "failed", "timed_out",
    name="simulationstatus",
)
_report_status = sa.Enum(
    "draft", "ready",
    name="reportstatus",
)


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # contracts
    # ------------------------------------------------------------------ #
    op.create_table(
        "contracts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("language", _contract_language, nullable=False),
        sa.Column("source", sa.Text, nullable=True),
        sa.Column("bytecode", sa.Text, nullable=True),
        sa.Column("compiler_version", sa.String(64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # ------------------------------------------------------------------ #
    # jobs
    # ------------------------------------------------------------------ #
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "contract_id",
            sa.String(36),
            sa.ForeignKey("contracts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", _job_status, nullable=False, server_default="pending"),
        sa.Column("tools", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("progress", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ------------------------------------------------------------------ #
    # findings
    # ------------------------------------------------------------------ #
    op.create_table(
        "findings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "job_id",
            sa.String(36),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tool", _tool_name, nullable=False),
        sa.Column("vulnerability_type", _vulnerability_type, nullable=False),
        sa.Column("severity", _severity, nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("location", sa.String(512), nullable=True),
        sa.Column(
            "confidence",
            sa.Float,
            nullable=False,
            server_default="0.5",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # ------------------------------------------------------------------ #
    # evidences
    # ------------------------------------------------------------------ #
    op.create_table(
        "evidences",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "finding_id",
            sa.String(36),
            sa.ForeignKey("findings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # ------------------------------------------------------------------ #
    # simulation_runs
    # ------------------------------------------------------------------ #
    op.create_table(
        "simulation_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "job_id",
            sa.String(36),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "finding_id",
            sa.String(36),
            sa.ForeignKey("findings.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "status",
            _simulation_status,
            nullable=False,
            server_default="queued",
        ),
        sa.Column("template", sa.String(64), nullable=False),
        sa.Column("fork_rpc_url", sa.String(512), nullable=True),
        sa.Column("fork_block", sa.Integer, nullable=True),
        sa.Column("trace", sa.Text, nullable=True),
        sa.Column("output", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ------------------------------------------------------------------ #
    # reports
    # ------------------------------------------------------------------ #
    op.create_table(
        "reports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "job_id",
            sa.String(36),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("status", _report_status, nullable=False, server_default="draft"),
        sa.Column("summary", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("markdown", sa.Text, nullable=True),
        sa.Column("html", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("reports")
    op.drop_table("simulation_runs")
    op.drop_table("evidences")
    op.drop_table("findings")
    op.drop_table("jobs")
    op.drop_table("contracts")

    # Drop PostgreSQL enum types (no-op on SQLite)
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for enum in (
            _report_status,
            _simulation_status,
            _tool_name,
            _vulnerability_type,
            _severity,
            _job_status,
            _contract_language,
        ):
            enum.drop(bind, checkfirst=True)
