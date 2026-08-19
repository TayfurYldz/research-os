"""SD-G6 OAST token table.

Revision ID: a30_001_oast_token
Revises: a29_001_hunter_family_registry
Create Date: 2026-08-19

Adds oast_token table for callback token provenance.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a30_001_oast_token"
down_revision: Union[str, Sequence[str], None] = "a29_001_hunter_family_registry"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "oast_token",
        sa.Column("token_id", sa.Text(), nullable=False),
        sa.Column("research_run_id", sa.Text(), nullable=False),
        sa.Column("hypothesis_id", sa.Text(), nullable=False),
        sa.Column("target_reference", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["research_run_id"],
            ["research_run.research_run_id"],
            name="fk_oast_token_research_run",
        ),
        sa.PrimaryKeyConstraint("token_id", name="pk_oast_token"),
        sa.UniqueConstraint(
            "token_id", "research_run_id", name="uq_oast_token_id_run"
        ),
    )


def downgrade() -> None:
    op.drop_table("oast_token")
