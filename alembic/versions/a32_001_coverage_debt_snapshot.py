"""SD-G8 coverage debt snapshot.

Revision ID: a32_001_coverage_debt_snapshot
Revises: a31_001_impact_graph
Create Date: 2026-08-19

Adds coverage_debt_snapshot: a durable summary of a rebuildable coverage debt
projection. The full matrix remains rebuildable from the graph + registry +
ledger; this table only stores hash + counts.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a32_001_coverage_debt_snapshot"
down_revision: Union[str, Sequence[str], None] = "a31_001_impact_graph"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "coverage_debt_snapshot",
        sa.Column("snapshot_id", sa.Text(), nullable=False),
        sa.Column(
            "research_run_id",
            sa.Text(),
            sa.ForeignKey("research_run.research_run_id"),
            nullable=False,
        ),
        sa.Column("matrix_hash", sa.Text(), nullable=False),
        sa.Column("cell_counts", postgresql.JSONB(), nullable=False),
        sa.Column("total_debt", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("snapshot_id", name="pk_coverage_debt_snapshot"),
        sa.UniqueConstraint(
            "snapshot_id", "research_run_id", name="uq_coverage_debt_snapshot_id_run"
        ),
        sa.CheckConstraint(
            "length(matrix_hash) = 64", name="ck_coverage_debt_snapshot_hash_length"
        ),
        sa.CheckConstraint(
            "total_debt >= 0", name="ck_coverage_debt_snapshot_total_debt"
        ),
    )


def downgrade() -> None:
    op.drop_table("coverage_debt_snapshot")
