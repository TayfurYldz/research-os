"""Append-only research reasoning provenance (Decisions 025–026).

Revision ID: a8_001_research_reasoning
Revises: a7_001_execution_attempt
Create Date: 2026-08-16

Adds research_reasoning for Generator/Falsifier structured output provenance.
Does not rewrite a3_001, a6_001, or a7_001.
Does not add Evidence, Candidate, or Finding.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a8_001_research_reasoning"
down_revision: Union[str, Sequence[str], None] = "a7_001_execution_attempt"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APPEND_ONLY_TRIGGER = """
CREATE TRIGGER trg_research_reasoning_append_only
BEFORE UPDATE OR DELETE ON research_reasoning
FOR EACH ROW
EXECUTE PROCEDURE research_os_reject_mutation();
"""


def upgrade() -> None:
    op.create_table(
        "research_reasoning",
        sa.Column("reasoning_record_id", sa.Text(), primary_key=True),
        sa.Column("research_run_id", sa.Text(), nullable=False),
        sa.Column("hypothesis_id", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("adapter_identity", sa.Text(), nullable=False),
        sa.Column("provider_adapter_identity", sa.Text(), nullable=False),
        sa.Column("correlation_id", sa.Text(), nullable=False),
        sa.Column("context_fingerprint", sa.Text(), nullable=False),
        sa.Column("structured_output", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("model_id", sa.Text(), nullable=True),
        sa.Column("model_version", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["hypothesis_id", "research_run_id"],
            ["hypothesis.hypothesis_id", "hypothesis.research_run_id"],
            name="fk_research_reasoning_hypothesis_same_run",
        ),
        sa.CheckConstraint(
            "role IN ('GENERATOR', 'FALSIFIER')",
            name="ck_research_reasoning_role",
        ),
    )
    op.execute(sa.text(APPEND_ONLY_TRIGGER))


def downgrade() -> None:
    op.execute(sa.text("DROP TRIGGER IF EXISTS trg_research_reasoning_append_only ON research_reasoning"))
    op.drop_table("research_reasoning")
