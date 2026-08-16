"""FindingProposal, Human Review, Approval, and Finding (Decisions 037–038 / GATE 06).

Revision ID: a12_001_finding_acceptance
Revises: a11_001_candidate_verification
Create Date: 2026-08-17

Does not rewrite a3–a11.
Finding is diagnostic plumbing, not a vulnerability. No CVSS/CVE/bounty.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a12_001_finding_acceptance"
down_revision: Union[str, Sequence[str], None] = "a11_001_candidate_verification"
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
        "finding_proposal",
        sa.Column("proposal_id", sa.Text(), primary_key=True),
        sa.Column("candidate_id", sa.Text(), nullable=False),
        sa.Column("research_run_id", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("claim", sa.Text(), nullable=False),
        sa.Column("classification", sa.Text(), nullable=False),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("evidence_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("verification_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("content_fingerprint", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["candidate.candidate_id"],
            name="fk_finding_proposal_candidate",
        ),
        sa.ForeignKeyConstraint(
            ["research_run_id"],
            ["research_run.research_run_id"],
            name="fk_finding_proposal_research_run",
        ),
        sa.CheckConstraint(
            "state IN ('PROPOSED', 'HUMAN_REVIEW', 'APPROVED', 'REJECTED')",
            name="ck_finding_proposal_state",
        ),
        sa.CheckConstraint(
            "classification IN ('DIAGNOSTIC_PLUMBING')",
            name="ck_finding_proposal_classification",
        ),
    )

    op.create_table(
        "human_review",
        sa.Column("review_id", sa.Text(), primary_key=True),
        sa.Column("proposal_id", sa.Text(), nullable=False),
        sa.Column("content_fingerprint", sa.Text(), nullable=False),
        sa.Column("decision", sa.Text(), nullable=False),
        sa.Column("reviewer_id", sa.Text(), nullable=False),
        sa.Column("actor_type", sa.Text(), nullable=False),
        sa.Column("reason_codes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["proposal_id"],
            ["finding_proposal.proposal_id"],
            name="fk_human_review_proposal",
        ),
        sa.UniqueConstraint(
            "proposal_id",
            "content_fingerprint",
            name="uq_human_review_proposal_fingerprint",
        ),
        sa.CheckConstraint(
            "decision IN ('APPROVE', 'REJECT')",
            name="ck_human_review_decision",
        ),
        sa.CheckConstraint(
            "actor_type IN ('HUMAN_OPERATOR', 'CONTROL_PLANE', 'WORKER', 'INTEGRATION')",
            name="ck_human_review_actor_type",
        ),
    )
    op.execute(
        sa.text(
            APPEND_ONLY_TRIGGER.format(
                name="trg_human_review_append_only", table="human_review"
            )
        )
    )

    op.create_table(
        "approval",
        sa.Column("approval_id", sa.Text(), primary_key=True),
        sa.Column("subject_reference", sa.Text(), nullable=False),
        sa.Column("decision", sa.Text(), nullable=False),
        sa.Column("decided_by", sa.Text(), nullable=False),
        sa.Column("actor_type", sa.Text(), nullable=False),
        sa.Column("recorded", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("research_run_id", sa.Text(), nullable=False),
        sa.Column("proposal_id", sa.Text(), nullable=False),
        sa.Column("human_review_id", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["research_run_id"],
            ["research_run.research_run_id"],
            name="fk_approval_research_run",
        ),
        sa.ForeignKeyConstraint(
            ["proposal_id"],
            ["finding_proposal.proposal_id"],
            name="fk_approval_proposal",
        ),
        sa.ForeignKeyConstraint(
            ["human_review_id"],
            ["human_review.review_id"],
            name="fk_approval_human_review",
        ),
        sa.UniqueConstraint("subject_reference", name="uq_approval_subject_reference"),
        sa.CheckConstraint(
            "decision IN ('APPROVE', 'REJECT')",
            name="ck_approval_decision",
        ),
        sa.CheckConstraint(
            "actor_type IN ('HUMAN_OPERATOR', 'CONTROL_PLANE', 'WORKER', 'INTEGRATION')",
            name="ck_approval_actor_type",
        ),
        sa.CheckConstraint("recorded IS TRUE", name="ck_approval_recorded"),
    )
    op.execute(
        sa.text(APPEND_ONLY_TRIGGER.format(name="trg_approval_append_only", table="approval"))
    )

    op.create_table(
        "finding",
        sa.Column("finding_id", sa.Text(), primary_key=True),
        sa.Column("finding_proposal_id", sa.Text(), nullable=False),
        sa.Column("candidate_id", sa.Text(), nullable=False),
        sa.Column("research_run_id", sa.Text(), nullable=False),
        sa.Column("approval_id", sa.Text(), nullable=False),
        sa.Column("human_review_id", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("claim", sa.Text(), nullable=False),
        sa.Column("classification", sa.Text(), nullable=False),
        sa.Column("evidence_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("verification_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["finding_proposal_id"],
            ["finding_proposal.proposal_id"],
            name="fk_finding_proposal",
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["candidate.candidate_id"],
            name="fk_finding_candidate",
        ),
        sa.ForeignKeyConstraint(
            ["research_run_id"],
            ["research_run.research_run_id"],
            name="fk_finding_research_run",
        ),
        sa.ForeignKeyConstraint(
            ["approval_id"],
            ["approval.approval_id"],
            name="fk_finding_approval",
        ),
        sa.ForeignKeyConstraint(
            ["human_review_id"],
            ["human_review.review_id"],
            name="fk_finding_human_review",
        ),
        sa.UniqueConstraint("finding_proposal_id", name="uq_finding_proposal_id"),
        sa.CheckConstraint(
            "classification IN ('DIAGNOSTIC_PLUMBING')",
            name="ck_finding_classification",
        ),
    )
    op.execute(
        sa.text(APPEND_ONLY_TRIGGER.format(name="trg_finding_append_only", table="finding"))
    )


def downgrade() -> None:
    op.execute(sa.text("DROP TRIGGER IF EXISTS trg_finding_append_only ON finding"))
    op.drop_table("finding")
    op.execute(sa.text("DROP TRIGGER IF EXISTS trg_approval_append_only ON approval"))
    op.drop_table("approval")
    op.execute(
        sa.text("DROP TRIGGER IF EXISTS trg_human_review_append_only ON human_review")
    )
    op.drop_table("human_review")
    op.drop_table("finding_proposal")
