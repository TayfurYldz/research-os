"""Add opportunity_selection_candidate (Slice 3 / Phase D, MR-1).

New, additive-only table. It is a durable pre-admission bridge: a producer
outside the diagnostic path (Hunter/Coverage today; source_system is a
closed enum so future producers must be added explicitly) proposes a
candidate here, and the existing SelectResearchOpportunities use case is the
sole reader/decider that turns a PENDING candidate into either an admitted
ResearchOpportunity row (existing research_opportunity table, unchanged) or
a recorded non-admission. This table never becomes a second
ResearchOpportunity authority.

Revision ID: a36_001_opportunity_candidate
Revises: a35_001_orchestration_lease
Create Date: 2026-08-21
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a36_001_opportunity_candidate"
down_revision: Union[str, Sequence[str], None] = "a35_001_orchestration_lease"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "opportunity_selection_candidate",
        sa.Column("candidate_id", sa.Text(), nullable=False),
        sa.Column(
            "research_run_id",
            sa.Text(),
            sa.ForeignKey("research_run.research_run_id"),
            nullable=False,
        ),
        sa.Column("source_system", sa.Text(), nullable=False),
        sa.Column("opportunity_kind", sa.Text(), nullable=False),
        sa.Column("mode", sa.Text(), nullable=False),
        sa.Column("source_refs", postgresql.JSONB(), nullable=False),
        sa.Column("proposed_direction", sa.Text(), nullable=False),
        sa.Column("unresolved_question", sa.Text(), nullable=False),
        sa.Column("expected_information_value_description", sa.Text(), nullable=False),
        sa.Column("assumptions", postgresql.JSONB(), nullable=False),
        sa.Column("dimensions", postgresql.JSONB(), nullable=False),
        sa.Column("context_signature", sa.Text(), nullable=False),
        sa.Column("structural_identity", sa.Text(), nullable=False),
        sa.Column("strategy_version", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "outcome", sa.Text(), nullable=False, server_default="PENDING"
        ),
        sa.Column("resulting_opportunity_id", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("candidate_id", name="pk_opportunity_selection_candidate"),
        sa.CheckConstraint(
            "source_system IN ('HUNTER_COVERAGE')",
            name="ck_opportunity_selection_candidate_source_system",
        ),
        sa.CheckConstraint(
            "mode IN ('EXPLORATION', 'EXPLOITATION')",
            name="ck_opportunity_selection_candidate_mode",
        ),
        sa.CheckConstraint(
            "outcome IN ('PENDING', 'ADMITTED', 'NOT_ADMITTED')",
            name="ck_opportunity_selection_candidate_outcome",
        ),
        sa.UniqueConstraint(
            "research_run_id",
            "structural_identity",
            name="uq_opportunity_selection_candidate_run_identity",
        ),
    )


def downgrade() -> None:
    op.drop_table("opportunity_selection_candidate")
