"""SD-G9 hypothesis identity binding.

Revision ID: a33_001_hypothesis_identity
Revises: a32_001_coverage_debt_snapshot
Create Date: 2026-08-19

Adds identity_id to hypothesis and hunt_v3_queue so hypotheses and their
active-experiment queue items are bound to a specific identity. NULL values
preserve the older identity-agnostic semantics used by SD-G8.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a33_001_hypothesis_identity"
down_revision: Union[str, Sequence[str], None] = "a32_001_coverage_debt_snapshot"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "hypothesis",
        sa.Column("identity_id", sa.Text(), nullable=True),
    )
    op.add_column(
        "hunt_v3_queue",
        sa.Column("identity_id", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("hunt_v3_queue", "identity_id")
    op.drop_column("hypothesis", "identity_id")
