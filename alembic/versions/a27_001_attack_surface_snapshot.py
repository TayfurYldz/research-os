"""SD-G3 attack surface graph snapshot.

Revision ID: a27_001_attack_surface_snapshot
Revises: a26_001_sensor_obs_src
Create Date: 2026-08-19

Adds attack_surface_snapshot: a durable summary of a rebuildable graph projection.
Node/edge data remains in the discovery ledger; this table only stores hash + counts.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a27_001_attack_surface_snapshot"
down_revision: Union[str, Sequence[str], None] = "a26_001_sensor_obs_src"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "attack_surface_snapshot",
        sa.Column("snapshot_id", sa.Text(), nullable=False),
        sa.Column(
            "research_run_id",
            sa.Text(),
            sa.ForeignKey("research_run.research_run_id"),
            nullable=False,
        ),
        sa.Column("strategy_version", sa.Text(), nullable=False),
        sa.Column("node_count", sa.Integer(), nullable=False),
        sa.Column("edge_count", sa.Integer(), nullable=False),
        sa.Column("graph_hash", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("snapshot_id"),
        sa.CheckConstraint("node_count >= 0", name="ck_attack_surface_snapshot_node_count"),
        sa.CheckConstraint("edge_count >= 0", name="ck_attack_surface_snapshot_edge_count"),
        sa.CheckConstraint("length(graph_hash) = 64", name="ck_attack_surface_snapshot_hash_length"),
    )


def downgrade() -> None:
    op.drop_table("attack_surface_snapshot")
