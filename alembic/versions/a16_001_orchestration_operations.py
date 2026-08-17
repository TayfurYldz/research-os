"""Orchestration checkpoint, cycle history, and budget consumption ledger (Decisions 049–050 / GATE 12–13).

Revision ID: a16_001_orchestration_operations
Revises: a15_001_exploration_temporal
Create Date: 2026-08-17

Does not rewrite a3–a15.
Orchestration state is not a Finding. BudgetConsumption is not IssuedBudget.
AuditEvent is not used as workflow state. PostgreSQL is not a message broker.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a16_001_orchestration_operations"
down_revision: Union[str, Sequence[str], None] = "a15_001_exploration_temporal"
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
        "research_orchestration",
        sa.Column("research_run_id", sa.Text(), primary_key=True),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("cycle_number", sa.Integer(), nullable=False),
        sa.Column("last_phase", sa.Text(), nullable=False),
        sa.Column("last_opportunity_id", sa.Text(), nullable=True),
        sa.Column("last_hypothesis_id", sa.Text(), nullable=True),
        sa.Column("last_experiment_id", sa.Text(), nullable=True),
        sa.Column("pause_reason", sa.Text(), nullable=True),
        sa.Column("stop_reason", sa.Text(), nullable=True),
        sa.Column("policy_version", sa.Text(), nullable=False),
        sa.Column("max_cycles", sa.Integer(), nullable=False),
        sa.Column("max_experiments", sa.Integer(), nullable=False),
        sa.Column("max_model_calls", sa.Integer(), nullable=False),
        sa.Column("max_worker_invocations", sa.Integer(), nullable=False),
        sa.Column("max_elapsed_ms", sa.Integer(), nullable=False),
        sa.Column("max_selected_opportunities", sa.Integer(), nullable=False),
        sa.Column("max_runtime_fallback", sa.Integer(), nullable=False),
        sa.Column("side_effect_ceiling", sa.Integer(), nullable=False),
        sa.Column("allow_repeated_control_experiments", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("checkpoint_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["research_run_id"],
            ["research_run.research_run_id"],
            name="fk_research_orchestration_research_run",
        ),
        sa.CheckConstraint(
            "state IN ("
            "'READY', 'RUNNING', 'PAUSED', 'WAITING_HUMAN', 'BLOCKED', "
            "'BUDGET_EXHAUSTED', 'COMPLETED', 'FAILED_OPERATIONAL')",
            name="ck_research_orchestration_state",
        ),
        sa.CheckConstraint("cycle_number >= 0", name="ck_research_orchestration_cycle_number"),
        sa.CheckConstraint("max_cycles >= 0", name="ck_research_orchestration_max_cycles"),
        sa.CheckConstraint("max_experiments >= 0", name="ck_research_orchestration_max_experiments"),
        sa.CheckConstraint("max_model_calls >= 0", name="ck_research_orchestration_max_model_calls"),
        sa.CheckConstraint(
            "max_worker_invocations >= 0",
            name="ck_research_orchestration_max_worker_invocations",
        ),
        sa.CheckConstraint("max_elapsed_ms >= 0", name="ck_research_orchestration_max_elapsed_ms"),
        sa.CheckConstraint(
            "max_selected_opportunities >= 0",
            name="ck_research_orchestration_max_selected_opportunities",
        ),
        sa.CheckConstraint(
            "max_runtime_fallback >= 0",
            name="ck_research_orchestration_max_runtime_fallback",
        ),
        sa.CheckConstraint(
            "side_effect_ceiling IN (0, 1, 2, 3)",
            name="ck_research_orchestration_side_effect_ceiling",
        ),
    )
    op.create_table(
        "research_cycle",
        sa.Column("cycle_id", sa.Text(), primary_key=True),
        sa.Column("research_run_id", sa.Text(), nullable=False),
        sa.Column("cycle_number", sa.Integer(), nullable=False),
        sa.Column("phase_completed", sa.Text(), nullable=False),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.Column("stop_reason", sa.Text(), nullable=True),
        sa.Column("opportunity_id", sa.Text(), nullable=True),
        sa.Column("hypothesis_id", sa.Text(), nullable=True),
        sa.Column("experiment_id", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["research_run_id"],
            ["research_run.research_run_id"],
            name="fk_research_cycle_research_run",
        ),
        sa.UniqueConstraint(
            "research_run_id",
            "cycle_number",
            name="uq_research_cycle_run_number",
        ),
        sa.CheckConstraint("cycle_number >= 0", name="ck_research_cycle_number"),
        sa.CheckConstraint(
            "outcome IN ("
            "'CONTINUE', 'PAUSE', 'COMPLETE', 'BLOCKED', 'REQUIRE_HUMAN_REVIEW')",
            name="ck_research_cycle_outcome",
        ),
    )
    op.execute(
        sa.text(
            APPEND_ONLY_TRIGGER.format(
                name="trg_research_cycle_append_only", table="research_cycle"
            )
        )
    )
    op.create_table(
        "budget_consumption",
        sa.Column("consumption_id", sa.Text(), primary_key=True),
        sa.Column("budget_id", sa.Text(), nullable=False),
        sa.Column("research_run_id", sa.Text(), nullable=False),
        sa.Column("experiment_id", sa.Text(), nullable=True),
        sa.Column("request_id", sa.Text(), nullable=True),
        sa.Column("resource_type", sa.Text(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("unit", sa.Text(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provenance", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["budget_id", "research_run_id"],
            ["issued_budget.budget_id", "issued_budget.research_run_id"],
            name="fk_budget_consumption_issued_budget_same_run",
        ),
        sa.UniqueConstraint(
            "budget_id",
            "request_id",
            "resource_type",
            name="uq_budget_consumption_request_resource",
        ),
        sa.CheckConstraint("amount > 0", name="ck_budget_consumption_amount_positive"),
        sa.CheckConstraint(
            "resource_type IN ("
            "'MODEL_CALL', 'WORKER_INVOCATION', 'REQUEST', "
            "'EXECUTION_TIME', 'ARTIFACT_BYTES', 'COST')",
            name="ck_budget_consumption_resource_type",
        ),
        sa.CheckConstraint(
            "unit IN ('count', 'milliseconds', 'bytes')",
            name="ck_budget_consumption_unit",
        ),
    )
    op.execute(
        sa.text(
            APPEND_ONLY_TRIGGER.format(
                name="trg_budget_consumption_append_only", table="budget_consumption"
            )
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP TRIGGER IF EXISTS trg_budget_consumption_append_only ON budget_consumption"))
    op.drop_table("budget_consumption")
    op.execute(sa.text("DROP TRIGGER IF EXISTS trg_research_cycle_append_only ON research_cycle"))
    op.drop_table("research_cycle")
    op.drop_table("research_orchestration")
