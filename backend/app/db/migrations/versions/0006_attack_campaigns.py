"""Add attack_campaigns table.

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-15
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "attack_campaigns",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("job_id", sa.String(36), sa.ForeignKey("jobs.id"), nullable=False, unique=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="queued"),
        sa.Column("attack_plan", sa.Text(), nullable=True),
        sa.Column("test_code", sa.Text(), nullable=True),
        sa.Column("output", sa.Text(), nullable=True),
        sa.Column("trace", sa.Text(), nullable=True),
        sa.Column("results", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_attack_campaigns_job_id", "attack_campaigns", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_attack_campaigns_job_id", "attack_campaigns")
    op.drop_table("attack_campaigns")
