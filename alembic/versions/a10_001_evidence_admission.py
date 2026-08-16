"""Evidence admission (Transition B / Decisions 033–034).

Revision ID: a10_001_evidence_admission
Revises: a9_001_learning_cycle
Create Date: 2026-08-17

Adds append-only evidence, evidence_observation, and evidence_admission.
Does not rewrite a3_001, a6_001, a7_001, a8_001, or a9_001.
Does not add Candidate, Finding, Verification, or FindingProposal.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a10_001_evidence_admission"
down_revision: Union[str, Sequence[str], None] = "a9_001_learning_cycle"
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
        "evidence",
        sa.Column("evidence_id", sa.Text(), primary_key=True),
        sa.Column("research_run_id", sa.Text(), nullable=False),
        sa.Column("hypothesis_id", sa.Text(), nullable=False),
        sa.Column("experiment_id", sa.Text(), nullable=False),
        sa.Column("admission_record_id", sa.Text(), nullable=False),
        sa.Column("polarity", sa.Text(), nullable=False),
        sa.Column("claim_scope", sa.Text(), nullable=False),
        sa.Column("observation_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("assessment_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["research_run_id"],
            ["research_run.research_run_id"],
            name="fk_evidence_research_run",
        ),
        sa.ForeignKeyConstraint(
            ["hypothesis_id", "research_run_id"],
            ["hypothesis.hypothesis_id", "hypothesis.research_run_id"],
            name="fk_evidence_hypothesis_same_run",
        ),
        sa.ForeignKeyConstraint(
            ["experiment_id", "research_run_id"],
            ["experiment.experiment_id", "experiment.research_run_id"],
            name="fk_evidence_experiment_same_run",
        ),
        sa.CheckConstraint(
            "polarity IN ('SUPPORTING', 'CONTRADICTING', 'NEUTRAL')",
            name="ck_evidence_polarity",
        ),
    )
    op.execute(
        sa.text(APPEND_ONLY_TRIGGER.format(name="trg_evidence_append_only", table="evidence"))
    )

    op.create_table(
        "evidence_observation",
        sa.Column("evidence_id", sa.Text(), nullable=False),
        sa.Column("observation_id", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("evidence_id", "observation_id"),
        sa.ForeignKeyConstraint(
            ["evidence_id"],
            ["evidence.evidence_id"],
            name="fk_evidence_observation_evidence",
        ),
        sa.ForeignKeyConstraint(
            ["observation_id"],
            ["observation.observation_id"],
            name="fk_evidence_observation_observation",
        ),
    )
    op.execute(
        sa.text(
            APPEND_ONLY_TRIGGER.format(
                name="trg_evidence_observation_append_only",
                table="evidence_observation",
            )
        )
    )

    op.create_table(
        "evidence_admission",
        sa.Column("admission_record_id", sa.Text(), primary_key=True),
        sa.Column("proposal_id", sa.Text(), nullable=False),
        sa.Column("research_run_id", sa.Text(), nullable=False),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.Column("reason_codes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("observation_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("assessment_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("admission_policy_version", sa.Text(), nullable=False),
        sa.Column("evaluator_version", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("admitted_evidence_id", sa.Text(), nullable=True),
        sa.Column("claim_scope", sa.Text(), nullable=True),
        sa.Column("polarity", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["research_run_id"],
            ["research_run.research_run_id"],
            name="fk_evidence_admission_research_run",
        ),
        sa.ForeignKeyConstraint(
            ["admitted_evidence_id"],
            ["evidence.evidence_id"],
            name="fk_evidence_admission_evidence",
        ),
        sa.CheckConstraint(
            "outcome IN ("
            "'ADMITTED', 'REJECTED_INSUFFICIENT_SUPPORT', 'REJECTED_BROKEN_PROVENANCE', "
            "'REJECTED_EXECUTION_UNUSABLE', 'REJECTED_POLICY_CONFLICT', "
            "'NEEDS_VERIFICATION')",
            name="ck_evidence_admission_outcome",
        ),
        sa.CheckConstraint(
            "(outcome = 'ADMITTED' AND admitted_evidence_id IS NOT NULL) OR "
            "(outcome <> 'ADMITTED' AND admitted_evidence_id IS NULL)",
            name="ck_evidence_admission_evidence_presence",
        ),
        sa.CheckConstraint(
            "polarity IS NULL OR polarity IN ('SUPPORTING', 'CONTRADICTING', 'NEUTRAL')",
            name="ck_evidence_admission_polarity",
        ),
    )
    op.execute(
        sa.text(
            APPEND_ONLY_TRIGGER.format(
                name="trg_evidence_admission_append_only",
                table="evidence_admission",
            )
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DROP TRIGGER IF EXISTS trg_evidence_admission_append_only ON evidence_admission"
        )
    )
    op.drop_table("evidence_admission")
    op.execute(
        sa.text(
            "DROP TRIGGER IF EXISTS trg_evidence_observation_append_only "
            "ON evidence_observation"
        )
    )
    op.drop_table("evidence_observation")
    op.execute(sa.text("DROP TRIGGER IF EXISTS trg_evidence_append_only ON evidence"))
    op.drop_table("evidence")
