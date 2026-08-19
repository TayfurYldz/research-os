"""SD-G2 sensor/acquisition plane.

Revision ID: a24_001_sensor_plane
Revises: a23_001_program_scope
Create Date: 2026-08-19

Sensor observations are raw, UNTRUSTED_EXTERNAL records. They become facts only
through the Research admission chain.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a24_001_sensor_plane"
down_revision: Union[str, Sequence[str], None] = "a23_001_program_scope"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sensor_observation",
        sa.Column("observation_id", sa.Text(), nullable=False),
        sa.Column("research_run_id", sa.Text(), nullable=False),
        sa.Column("sensor_id", sa.Text(), nullable=False),
        sa.Column("target_reference", sa.Text(), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload_digest", sa.Text(), nullable=False),
        sa.Column("epistemic_status", sa.Text(), nullable=False),
        sa.Column("source_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["research_run_id"],
            ["research_run.research_run_id"],
            name="fk_sensor_observation_research_run",
        ),
        sa.PrimaryKeyConstraint("observation_id"),
        sa.UniqueConstraint(
            "observation_id",
            "research_run_id",
            name="uq_sensor_observation_id_run",
        ),
        sa.CheckConstraint(
            "epistemic_status = 'UNTRUSTED_EXTERNAL'",
            name="ck_sensor_observation_epistemic",
        ),
    )


def downgrade() -> None:
    op.drop_table("sensor_observation")
