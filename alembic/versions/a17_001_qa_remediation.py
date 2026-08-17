"""QA remediation: durable orchestration config fingerprint and cycle phase refs.

Revision ID: a17_001_qa_remediation
Revises: a16_001_orchestration_operations
Create Date: 2026-08-17

Does not rewrite a3–a16.
Orchestration configuration fingerprint is integrity, not authorization.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a17_001_qa_remediation"
down_revision: Union[str, Sequence[str], None] = "a16_001_orchestration_operations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "research_orchestration",
        sa.Column("budget_id", sa.Text(), nullable=False, server_default="budget-unset"),
    )
    op.add_column(
        "research_orchestration",
        sa.Column("target_reference", sa.Text(), nullable=False, server_default="target-unset"),
    )
    op.add_column(
        "research_orchestration",
        sa.Column(
            "research_question",
            sa.Text(),
            nullable=False,
            server_default="diagnostic-question-unset",
        ),
    )
    op.add_column(
        "research_orchestration",
        sa.Column(
            "configuration_fingerprint",
            sa.Text(),
            nullable=False,
            server_default="0" * 64,
        ),
    )
    op.add_column(
        "research_orchestration",
        sa.Column(
            "current_phase",
            sa.Text(),
            nullable=False,
            server_default="CYCLE_READY",
        ),
    )
    op.add_column("research_orchestration", sa.Column("active_cycle_id", sa.Text(), nullable=True))
    op.add_column("research_orchestration", sa.Column("last_attempt_id", sa.Text(), nullable=True))
    op.add_column(
        "research_orchestration", sa.Column("last_observation_id", sa.Text(), nullable=True)
    )
    op.add_column(
        "research_orchestration", sa.Column("last_assessment_id", sa.Text(), nullable=True)
    )
    op.add_column(
        "research_orchestration", sa.Column("last_worker_result_id", sa.Text(), nullable=True)
    )
    op.add_column(
        "research_orchestration", sa.Column("routing_policy_version", sa.Text(), nullable=True)
    )
    op.add_column(
        "research_orchestration", sa.Column("scope_fingerprint", sa.Text(), nullable=True)
    )
    op.create_check_constraint(
        "ck_research_orchestration_current_phase",
        "research_orchestration",
        "current_phase IN ("
        "'CYCLE_READY', 'OPPORTUNITY_SELECTED', 'HYPOTHESIS_ADMITTED', "
        "'EXPERIMENT_PLANNED', 'AUTHORIZATION_REQUESTED', 'ATTEMPT_AUTHORIZED', "
        "'DISPATCHING', 'WORKER_RESULT_RECORDED', 'TRANSITION_A_COMPLETE', "
        "'ASSESSMENT_COMPLETE', 'TRANSITION_B_COMPLETE', 'CYCLE_COMPLETE')",
    )
    op.alter_column("research_orchestration", "budget_id", server_default=None)
    op.alter_column("research_orchestration", "target_reference", server_default=None)
    op.alter_column("research_orchestration", "research_question", server_default=None)
    op.alter_column("research_orchestration", "configuration_fingerprint", server_default=None)
    op.alter_column("research_orchestration", "current_phase", server_default=None)


def downgrade() -> None:
    op.drop_constraint(
        "ck_research_orchestration_current_phase",
        "research_orchestration",
        type_="check",
    )
    for column in (
        "scope_fingerprint",
        "routing_policy_version",
        "last_worker_result_id",
        "last_assessment_id",
        "last_observation_id",
        "last_attempt_id",
        "active_cycle_id",
        "current_phase",
        "configuration_fingerprint",
        "research_question",
        "target_reference",
        "budget_id",
    ):
        op.drop_column("research_orchestration", column)
