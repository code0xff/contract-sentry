"""Add tool_errors to jobs.

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-15
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("tool_errors", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("jobs", "tool_errors")
