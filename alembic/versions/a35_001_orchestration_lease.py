"""Add fenced lease fields to research_orchestration (Slice 1 / Phase B).

Additive only: three nullable/defaulted columns supporting a minimal
CAS-based ownership lease (owner_runtime_instance_id, lease_epoch,
lease_expires_at) on the existing authoritative orchestration checkpoint
row. No new table; no change to existing columns; safe for all current
rows (lease_epoch defaults to 0, meaning "never leased").

Revision ID: a35_001_orchestration_lease
Revises: a34_001_program_platforms
Create Date: 2026-08-21
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a35_001_orchestration_lease"
down_revision: Union[str, Sequence[str], None] = "a34_001_program_platforms"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "research_orchestration",
        sa.Column("owner_runtime_instance_id", sa.Text(), nullable=True),
    )
    op.add_column(
        "research_orchestration",
        sa.Column(
            "lease_epoch",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "research_orchestration",
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "ck_research_orchestration_lease_epoch",
        "research_orchestration",
        "lease_epoch >= 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_research_orchestration_lease_epoch",
        "research_orchestration",
        type_="check",
    )
    op.drop_column("research_orchestration", "lease_expires_at")
    op.drop_column("research_orchestration", "lease_epoch")
    op.drop_column("research_orchestration", "owner_runtime_instance_id")
