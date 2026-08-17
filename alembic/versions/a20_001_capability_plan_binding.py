"""Persist capability definition identity on experiment_plan.

Revision ID: a20_001_capability_plan_binding
Revises: a19_001_http_state_class
Create Date: 2026-08-17

T0 plans compiled under definition AAA must remain distinguishable from T1
definition BBB after restart. No backfill: legacy rows stay NULL.
Does not duplicate these columns onto execution_attempt.
Does not add a compiled-scope fingerprint column.
Does not rewrite GATE 16 Candidate/Finding CHECKs.
alembic_version.version_num is VARCHAR(32); keep revision ids within that bound.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a20_001_capability_plan_binding"
down_revision: Union[str, Sequence[str], None] = "a19_001_http_state_class"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "experiment_plan",
        sa.Column("capability_version", sa.Text(), nullable=True),
    )
    op.add_column(
        "experiment_plan",
        sa.Column("capability_definition_fingerprint", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("experiment_plan", "capability_definition_fingerprint")
    op.drop_column("experiment_plan", "capability_version")
