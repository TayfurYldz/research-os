"""Closed research learning cycle (Decisions 027–028 / GATE 03).

Revision ID: a9_001_learning_cycle
Revises: a8_001_research_reasoning
Create Date: 2026-08-17

Makes research_reasoning.hypothesis_id nullable for rejected reasoning.
Adds research_admission, experiment_plan, and hypothesis_assessment.
Does not rewrite a3_001, a6_001, a7_001, or a8_001.
Does not add Evidence, Candidate, or Finding.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a9_001_learning_cycle"
down_revision: Union[str, Sequence[str], None] = "a8_001_research_reasoning"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APPEND_ONLY_TRIGGER = """
CREATE TRIGGER {name}
BEFORE UPDATE OR DELETE ON {table}
FOR EACH ROW
EXECUTE PROCEDURE research_os_reject_mutation();
"""


def upgrade() -> None:
    op.drop_constraint(
        "fk_research_reasoning_hypothesis_same_run",
        "research_reasoning",
        type_="foreignkey",
    )
    op.alter_column(
        "research_reasoning",
        "hypothesis_id",
        existing_type=sa.Text(),
        nullable=True,
    )
    op.create_foreign_key(
        "fk_research_reasoning_research_run",
        "research_reasoning",
        "research_run",
        ["research_run_id"],
        ["research_run_id"],
    )
    op.create_foreign_key(
        "fk_research_reasoning_hypothesis_same_run",
        "research_reasoning",
        "hypothesis",
        ["hypothesis_id", "research_run_id"],
        ["hypothesis_id", "research_run_id"],
    )

    op.create_table(
        "research_admission",
        sa.Column("admission_record_id", sa.Text(), primary_key=True),
        sa.Column("research_run_id", sa.Text(), nullable=False),
        sa.Column("generator_reasoning_record_id", sa.Text(), nullable=True),
        sa.Column("falsifier_reasoning_record_id", sa.Text(), nullable=True),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.Column("admitted_hypothesis_id", sa.Text(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("reason_code", sa.Text(), nullable=False),
        sa.Column("context_fingerprint", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["research_run_id"],
            ["research_run.research_run_id"],
            name="fk_research_admission_research_run",
        ),
        sa.ForeignKeyConstraint(
            ["generator_reasoning_record_id"],
            ["research_reasoning.reasoning_record_id"],
            name="fk_research_admission_generator_reasoning",
        ),
        sa.ForeignKeyConstraint(
            ["falsifier_reasoning_record_id"],
            ["research_reasoning.reasoning_record_id"],
            name="fk_research_admission_falsifier_reasoning",
        ),
        sa.ForeignKeyConstraint(
            ["admitted_hypothesis_id", "research_run_id"],
            ["hypothesis.hypothesis_id", "hypothesis.research_run_id"],
            name="fk_research_admission_hypothesis_same_run",
        ),
        sa.CheckConstraint(
            "outcome IN ("
            "'ADMITTED', 'REJECTED_UNTESTABLE', 'REJECTED_UNSUPPORTED', "
            "'REJECTED_POLICY_CONFLICT', 'NEEDS_MORE_CONTEXT', "
            "'MODEL_INVOCATION_FAILED')",
            name="ck_research_admission_outcome",
        ),
        sa.CheckConstraint(
            "(outcome = 'ADMITTED' AND admitted_hypothesis_id IS NOT NULL) OR "
            "(outcome <> 'ADMITTED' AND admitted_hypothesis_id IS NULL)",
            name="ck_research_admission_hypothesis_presence",
        ),
    )
    op.execute(
        sa.text(
            APPEND_ONLY_TRIGGER.format(
                name="trg_research_admission_append_only",
                table="research_admission",
            )
        )
    )

    op.create_table(
        "experiment_plan",
        sa.Column("experiment_id", sa.Text(), primary_key=True),
        sa.Column("research_run_id", sa.Text(), nullable=False),
        sa.Column("hypothesis_id", sa.Text(), nullable=False),
        sa.Column("required_capability", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("target_reference", sa.Text(), nullable=False),
        sa.Column("side_effect_level", sa.Integer(), nullable=False),
        sa.Column("arguments", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("requested_budget_id", sa.Text(), nullable=False),
        sa.Column("expected_observation", sa.Text(), nullable=False),
        sa.Column("disconfirming_observation", sa.Text(), nullable=False),
        sa.Column("evaluation_strategy", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["experiment_id", "research_run_id"],
            ["experiment.experiment_id", "experiment.research_run_id"],
            name="fk_experiment_plan_experiment_same_run",
        ),
        sa.ForeignKeyConstraint(
            ["hypothesis_id", "research_run_id"],
            ["hypothesis.hypothesis_id", "hypothesis.research_run_id"],
            name="fk_experiment_plan_hypothesis_same_run",
        ),
        sa.ForeignKeyConstraint(
            ["requested_budget_id", "research_run_id"],
            ["issued_budget.budget_id", "issued_budget.research_run_id"],
            name="fk_experiment_plan_budget_same_run",
        ),
        sa.UniqueConstraint("experiment_id", "research_run_id", name="uq_experiment_plan_id_run"),
        sa.CheckConstraint(
            "side_effect_level IN (0, 1, 2, 3)",
            name="ck_experiment_plan_side_effect_level",
        ),
    )
    op.execute(
        sa.text(
            APPEND_ONLY_TRIGGER.format(
                name="trg_experiment_plan_append_only",
                table="experiment_plan",
            )
        )
    )

    op.create_table(
        "hypothesis_assessment",
        sa.Column("assessment_id", sa.Text(), primary_key=True),
        sa.Column("hypothesis_id", sa.Text(), nullable=False),
        sa.Column("experiment_id", sa.Text(), nullable=False),
        sa.Column("research_run_id", sa.Text(), nullable=False),
        sa.Column("assessment_outcome", sa.Text(), nullable=False),
        sa.Column(
            "observation_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("evaluator_kind", sa.Text(), nullable=False),
        sa.Column("evaluator_version", sa.Text(), nullable=False),
        sa.Column("rationale", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("evaluation_strategy", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["hypothesis_id", "research_run_id"],
            ["hypothesis.hypothesis_id", "hypothesis.research_run_id"],
            name="fk_hypothesis_assessment_hypothesis_same_run",
        ),
        sa.ForeignKeyConstraint(
            ["experiment_id", "research_run_id"],
            ["experiment.experiment_id", "experiment.research_run_id"],
            name="fk_hypothesis_assessment_experiment_same_run",
        ),
        sa.CheckConstraint(
            "assessment_outcome IN ("
            "'CONSISTENT_WITH_PREDICTION', 'CONTRADICTS_PREDICTION', "
            "'INCONCLUSIVE', 'EXECUTION_UNUSABLE', 'NEEDS_MORE_CONTEXT')",
            name="ck_hypothesis_assessment_outcome",
        ),
        sa.CheckConstraint(
            "evaluator_kind IN ('DETERMINISTIC')",
            name="ck_hypothesis_assessment_evaluator_kind",
        ),
    )
    op.execute(
        sa.text(
            APPEND_ONLY_TRIGGER.format(
                name="trg_hypothesis_assessment_append_only",
                table="hypothesis_assessment",
            )
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DROP TRIGGER IF EXISTS trg_hypothesis_assessment_append_only "
            "ON hypothesis_assessment"
        )
    )
    op.drop_table("hypothesis_assessment")
    op.execute(
        sa.text("DROP TRIGGER IF EXISTS trg_experiment_plan_append_only ON experiment_plan")
    )
    op.drop_table("experiment_plan")
    op.execute(
        sa.text(
            "DROP TRIGGER IF EXISTS trg_research_admission_append_only ON research_admission"
        )
    )
    op.drop_table("research_admission")
    op.drop_constraint(
        "fk_research_reasoning_hypothesis_same_run",
        "research_reasoning",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_research_reasoning_research_run",
        "research_reasoning",
        type_="foreignkey",
    )
    op.alter_column(
        "research_reasoning",
        "hypothesis_id",
        existing_type=sa.Text(),
        nullable=False,
    )
    op.create_foreign_key(
        "fk_research_reasoning_hypothesis_same_run",
        "research_reasoning",
        "hypothesis",
        ["hypothesis_id", "research_run_id"],
        ["hypothesis_id", "research_run_id"],
    )
