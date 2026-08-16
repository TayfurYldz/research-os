"""Candidate lifecycle and Verification records (Decisions 035–036 / GATE 05).

Revision ID: a11_001_candidate_verification
Revises: a10_001_evidence_admission
Create Date: 2026-08-17

Adds candidate (mutable lifecycle state only), candidate_evidence,
candidate_admission, and append-only verification.
Does not rewrite a3_001, a6_001, a7_001, a8_001, a9_001, or a10_001.
Does not add Finding, FindingProposal, Human Review, or Approval.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a11_001_candidate_verification"
down_revision: Union[str, Sequence[str], None] = "a10_001_evidence_admission"
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
        "candidate",
        sa.Column("candidate_id", sa.Text(), primary_key=True),
        sa.Column("research_run_id", sa.Text(), nullable=False),
        sa.Column("hypothesis_id", sa.Text(), nullable=False),
        sa.Column("claim", sa.Text(), nullable=False),
        sa.Column("classification", sa.Text(), nullable=False),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("evidence_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("admission_record_id", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["research_run_id"],
            ["research_run.research_run_id"],
            name="fk_candidate_research_run",
        ),
        sa.ForeignKeyConstraint(
            ["hypothesis_id", "research_run_id"],
            ["hypothesis.hypothesis_id", "hypothesis.research_run_id"],
            name="fk_candidate_hypothesis_same_run",
        ),
        sa.CheckConstraint(
            "state IN ("
            "'OPEN', 'VERIFYING', 'VALIDATED', 'REJECTED', "
            "'INCONCLUSIVE', 'DUPLICATE', 'OUT_OF_SCOPE')",
            name="ck_candidate_state",
        ),
        sa.CheckConstraint(
            "classification IN ('DIAGNOSTIC_PLUMBING')",
            name="ck_candidate_classification",
        ),
    )

    op.create_table(
        "candidate_evidence",
        sa.Column("candidate_id", sa.Text(), nullable=False),
        sa.Column("evidence_id", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("candidate_id", "evidence_id"),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["candidate.candidate_id"],
            name="fk_candidate_evidence_candidate",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_id"],
            ["evidence.evidence_id"],
            name="fk_candidate_evidence_evidence",
        ),
    )
    op.execute(
        sa.text(
            APPEND_ONLY_TRIGGER.format(
                name="trg_candidate_evidence_append_only",
                table="candidate_evidence",
            )
        )
    )

    op.create_table(
        "candidate_admission",
        sa.Column("admission_record_id", sa.Text(), primary_key=True),
        sa.Column("proposal_id", sa.Text(), nullable=False),
        sa.Column("research_run_id", sa.Text(), nullable=False),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.Column("reason_codes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("evidence_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("admission_policy_version", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("admitted_candidate_id", sa.Text(), nullable=True),
        sa.Column("claim", sa.Text(), nullable=True),
        sa.Column("classification", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["research_run_id"],
            ["research_run.research_run_id"],
            name="fk_candidate_admission_research_run",
        ),
        sa.ForeignKeyConstraint(
            ["admitted_candidate_id"],
            ["candidate.candidate_id"],
            name="fk_candidate_admission_candidate",
        ),
        sa.CheckConstraint(
            "outcome IN ("
            "'ADMITTED', 'REJECTED_INSUFFICIENT_SUPPORT', 'REJECTED_BROKEN_PROVENANCE', "
            "'REJECTED_CLAIM_EXCEEDS_EVIDENCE', 'REJECTED_NOT_TESTABLE', "
            "'REJECTED_POLICY_CONFLICT')",
            name="ck_candidate_admission_outcome",
        ),
        sa.CheckConstraint(
            "(outcome = 'ADMITTED' AND admitted_candidate_id IS NOT NULL) OR "
            "(outcome <> 'ADMITTED' AND admitted_candidate_id IS NULL)",
            name="ck_candidate_admission_candidate_presence",
        ),
        sa.CheckConstraint(
            "classification IS NULL OR classification IN ('DIAGNOSTIC_PLUMBING')",
            name="ck_candidate_admission_classification",
        ),
    )
    op.execute(
        sa.text(
            APPEND_ONLY_TRIGGER.format(
                name="trg_candidate_admission_append_only",
                table="candidate_admission",
            )
        )
    )

    op.create_table(
        "verification",
        sa.Column("verification_id", sa.Text(), primary_key=True),
        sa.Column("candidate_id", sa.Text(), nullable=False),
        sa.Column("research_run_id", sa.Text(), nullable=False),
        sa.Column("strategy", sa.Text(), nullable=False),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.Column("proposed_candidate_state", sa.Text(), nullable=False),
        sa.Column("original_evidence_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("reproduction_evidence_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("negative_control_evidence_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("alternative_explanation_checks", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("verifier_kind", sa.Text(), nullable=False),
        sa.Column("verifier_identity", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["candidate.candidate_id"],
            name="fk_verification_candidate",
        ),
        sa.ForeignKeyConstraint(
            ["research_run_id"],
            ["research_run.research_run_id"],
            name="fk_verification_research_run",
        ),
        sa.CheckConstraint(
            "outcome IN ("
            "'VALIDATED', 'REJECTED', 'INCONCLUSIVE', 'DUPLICATE', 'OUT_OF_SCOPE')",
            name="ck_verification_outcome",
        ),
        sa.CheckConstraint(
            "proposed_candidate_state IN ("
            "'OPEN', 'VERIFYING', 'VALIDATED', 'REJECTED', "
            "'INCONCLUSIVE', 'DUPLICATE', 'OUT_OF_SCOPE')",
            name="ck_verification_proposed_state",
        ),
        sa.CheckConstraint(
            "proposed_candidate_state = outcome",
            name="ck_verification_proposed_matches_outcome",
        ),
        sa.CheckConstraint(
            "verifier_kind IN ('DETERMINISTIC')",
            name="ck_verification_verifier_kind",
        ),
    )
    op.execute(
        sa.text(
            APPEND_ONLY_TRIGGER.format(
                name="trg_verification_append_only",
                table="verification",
            )
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP TRIGGER IF EXISTS trg_verification_append_only ON verification"))
    op.drop_table("verification")
    op.execute(
        sa.text(
            "DROP TRIGGER IF EXISTS trg_candidate_admission_append_only ON candidate_admission"
        )
    )
    op.drop_table("candidate_admission")
    op.execute(
        sa.text(
            "DROP TRIGGER IF EXISTS trg_candidate_evidence_append_only ON candidate_evidence"
        )
    )
    op.drop_table("candidate_evidence")
    op.drop_table("candidate")
