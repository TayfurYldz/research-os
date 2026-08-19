"""SD-G2 sensor observation source link.

Revision ID: a26_001_sensor_obs_src
Revises: a25_001_discovery_fact_kinds
Create Date: 2026-08-19

Adds sensor_observation_id to discovery_fact_source so sensor-derived facts
carry provenance without colliding with worker-result observation_id.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a26_001_sensor_obs_src"
down_revision: Union[str, Sequence[str], None] = "a25_001_discovery_fact_kinds"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ONE_PRIMARY = (
    "(CASE WHEN {a} IS NOT NULL THEN 1 ELSE 0 END + "
    "CASE WHEN {b} IS NOT NULL THEN 1 ELSE 0 END + "
    "CASE WHEN {c} IS NOT NULL THEN 1 ELSE 0 END + "
    "CASE WHEN {d} IS NOT NULL THEN 1 ELSE 0 END + "
    "CASE WHEN {e} IS NOT NULL THEN 1 ELSE 0 END) = 1"
)


def upgrade() -> None:
    op.add_column(
        "discovery_fact_source",
        sa.Column("sensor_observation_id", sa.Text(), nullable=True),
    )
    op.create_foreign_key(
        "fk_discovery_fact_source_sensor_observation",
        "discovery_fact_source",
        "sensor_observation",
        ["sensor_observation_id"],
        ["observation_id"],
    )
    op.drop_constraint(
        "ck_discovery_fact_source_one_primary", "discovery_fact_source", type_="check"
    )
    op.create_check_constraint(
        "ck_discovery_fact_source_one_primary",
        "discovery_fact_source",
        ONE_PRIMARY.format(
            a="observation_id",
            b="sensor_observation_id",
            c="control_event_id",
            d="source_fact_id",
            e="source_inference_id",
        ),
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_discovery_fact_source_one_primary", "discovery_fact_source", type_="check"
    )
    op.create_check_constraint(
        "ck_discovery_fact_source_one_primary",
        "discovery_fact_source",
        "(CASE WHEN observation_id IS NOT NULL THEN 1 ELSE 0 END + "
        "CASE WHEN control_event_id IS NOT NULL THEN 1 ELSE 0 END + "
        "CASE WHEN source_fact_id IS NOT NULL THEN 1 ELSE 0 END + "
        "CASE WHEN source_inference_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
    )
    op.drop_constraint(
        "fk_discovery_fact_source_sensor_observation",
        "discovery_fact_source",
        type_="foreignkey",
    )
    op.drop_column("discovery_fact_source", "sensor_observation_id")
