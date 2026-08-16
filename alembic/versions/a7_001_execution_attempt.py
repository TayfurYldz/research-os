"""Durable ExecutionAttempt coordination state (Decision 024).

Revision ID: a7_001_execution_attempt
Revises: a6_001_transition_a_provenance
Create Date: 2026-08-16

Adds first-class execution_attempt for one intended Worker invocation.
Does not rewrite a3_001 or a6_001. Does not add Evidence/Candidate/Finding.
AuditEvent remains reconstructive provenance, not this table.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a7_001_execution_attempt"
down_revision: Union[str, Sequence[str], None] = "a6_001_transition_a_provenance"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "execution_attempt",
        sa.Column("attempt_id", sa.Text(), primary_key=True),
        sa.Column("request_id", sa.Text(), nullable=False),
        sa.Column("experiment_id", sa.Text(), nullable=False),
        sa.Column("research_run_id", sa.Text(), nullable=False),
        sa.Column("correlation_id", sa.Text(), nullable=False),
        sa.Column("worker_capability", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("target_reference", sa.Text(), nullable=False),
        sa.Column("budget_id", sa.Text(), nullable=False),
        sa.Column("side_effect_level", sa.Integer(), nullable=False),
        sa.Column("authorization_decision_reference", sa.Text(), nullable=False),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("authorized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dispatch_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["experiment_id", "research_run_id"],
            ["experiment.experiment_id", "experiment.research_run_id"],
            name="fk_execution_attempt_experiment_same_run",
        ),
        sa.ForeignKeyConstraint(
            ["budget_id", "research_run_id"],
            ["issued_budget.budget_id", "issued_budget.research_run_id"],
            name="fk_execution_attempt_budget_same_run",
        ),
        sa.ForeignKeyConstraint(
            ["authorization_decision_reference"],
            ["audit_event.audit_event_id"],
            name="fk_execution_attempt_authorization_decision",
        ),
        sa.UniqueConstraint("request_id", name="uq_execution_attempt_request_id"),
        sa.CheckConstraint(
            "state IN ("
            "'AUTHORIZED', 'DISPATCHING', 'COMPLETED', 'FAILED', "
            "'TIMED_OUT', 'CANCELLED', 'UNKNOWN_OUTCOME')",
            name="ck_execution_attempt_state",
        ),
        sa.CheckConstraint(
            "side_effect_level IN (0, 1, 2, 3)",
            name="ck_execution_attempt_side_effect_level",
        ),
    )


def downgrade() -> None:
    op.drop_table("execution_attempt")
