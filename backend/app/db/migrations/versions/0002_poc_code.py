"""Add poc_code to findings and simulation_runs.

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-14
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("findings", sa.Column("poc_code", sa.Text(), nullable=True))
    op.add_column("simulation_runs", sa.Column("poc_code", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("simulation_runs", "poc_code")
    op.drop_column("findings", "poc_code")
