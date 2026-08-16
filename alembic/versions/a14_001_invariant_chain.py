"""Invariant hypothesis and chain hypothesis records (Decisions 041–042 / GATE 08).

Revision ID: a14_001_invariant_chain
Revises: a13_001_target_differential
Create Date: 2026-08-17

Does not rewrite a3–a13.
Invariant hypothesis is not a fact. Chain hypothesis is not an exploit.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a14_001_invariant_chain"
down_revision: Union[str, Sequence[str], None] = "a13_001_target_differential"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APPEND_ONLY_TRIGGER = """
CREATE TRIGGER {name}
BEFORE UPDATE OR DELETE ON {table}
FOR EACH ROW
EXECUTE PROCEDURE research_os_reject_mutation();
"""


def upgrade() -> None:
    op.create_table(
        "invariant_hypothesis",
        sa.Column("invariant_id", sa.Text(), primary_key=True),
        sa.Column("research_run_id", sa.Text(), nullable=False),
        sa.Column("invariant_kind", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("subject_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("expected_behavior", sa.Text(), nullable=False),
        sa.Column("source_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "applicability_context",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("assumptions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "counterexample_refs",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("falsification_direction", sa.Text(), nullable=False),
        sa.Column("proposer_provenance", sa.Text(), nullable=False),
        sa.Column("strategy_version", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["research_run_id"],
            ["research_run.research_run_id"],
            name="fk_invariant_hypothesis_research_run",
        ),
        sa.CheckConstraint(
            "status IN ('TESTABLE', 'CHALLENGED', 'RETIRED')",
            name="ck_invariant_hypothesis_status",
        ),
        sa.CheckConstraint(
            "invariant_kind IN ("
            "'ACCESS_RELATION', 'STATE_TRANSITION', 'OWNERSHIP_RELATION', "
            "'ROLE_BOUNDARY', 'SESSION_BINDING', 'RESOURCE_ISOLATION', "
            "'IMMUTABILITY_AFTER_STATE', 'SEQUENCE_PRECONDITION', "
            "'INPUT_OUTPUT_RELATION', 'OTHER')",
            name="ck_invariant_hypothesis_kind",
        ),
    )
    op.create_table(
        "invariant_source_ref",
        sa.Column("invariant_id", sa.Text(), primary_key=True),
        sa.Column("source_ref", sa.Text(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["invariant_id"],
            ["invariant_hypothesis.invariant_id"],
            name="fk_invariant_source_ref_invariant",
        ),
    )
    op.execute(
        sa.text(
            APPEND_ONLY_TRIGGER.format(
                name="trg_invariant_source_ref_append_only", table="invariant_source_ref"
            )
        )
    )
    op.create_table(
        "invariant_counterexample_ref",
        sa.Column("counterexample_id", sa.Text(), primary_key=True),
        sa.Column("invariant_id", sa.Text(), nullable=False),
        sa.Column("source_ref", sa.Text(), nullable=False),
        sa.Column(
            "applicability_context",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["invariant_id"],
            ["invariant_hypothesis.invariant_id"],
            name="fk_invariant_counterexample_ref_invariant",
        ),
    )
    op.execute(
        sa.text(
            APPEND_ONLY_TRIGGER.format(
                name="trg_invariant_counterexample_ref_append_only",
                table="invariant_counterexample_ref",
            )
        )
    )
    op.create_table(
        "chain_hypothesis",
        sa.Column("chain_id", sa.Text(), primary_key=True),
        sa.Column("research_run_id", sa.Text(), nullable=False),
        sa.Column("structural_identity", sa.Text(), nullable=False),
        sa.Column("steps", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("preconditions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("expected_resulting_capability", sa.Text(), nullable=False),
        sa.Column(
            "unresolved_assumptions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "falsification_points",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "descriptive_features",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("strategy_version", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["research_run_id"],
            ["research_run.research_run_id"],
            name="fk_chain_hypothesis_research_run",
        ),
        sa.UniqueConstraint(
            "research_run_id",
            "structural_identity",
            name="uq_chain_hypothesis_run_identity",
        ),
    )
    op.execute(
        sa.text(
            APPEND_ONLY_TRIGGER.format(
                name="trg_chain_hypothesis_append_only", table="chain_hypothesis"
            )
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text("DROP TRIGGER IF EXISTS trg_chain_hypothesis_append_only ON chain_hypothesis")
    )
    op.drop_table("chain_hypothesis")
    op.execute(
        sa.text(
            "DROP TRIGGER IF EXISTS trg_invariant_counterexample_ref_append_only "
            "ON invariant_counterexample_ref"
        )
    )
    op.drop_table("invariant_counterexample_ref")
    op.execute(
        sa.text(
            "DROP TRIGGER IF EXISTS trg_invariant_source_ref_append_only "
            "ON invariant_source_ref"
        )
    )
    op.drop_table("invariant_source_ref")
    op.drop_table("invariant_hypothesis")
