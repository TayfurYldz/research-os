"""initial persistence spine

Revision ID: a3_001_persistence_spine
Revises:
Create Date: 2026-08-16

A3 authoritative persistence spine only. Not the full domain schema.
Evidence, Candidate, Finding, Approval, ScopeRule, and related tables are deferred.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a3_001_persistence_spine"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APPEND_ONLY_SQL = """
CREATE OR REPLACE FUNCTION research_os_reject_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'append-only: updates and deletes are forbidden on %', TG_TABLE_NAME;
END;
$$;

CREATE TRIGGER trg_issued_budget_append_only
BEFORE UPDATE OR DELETE ON issued_budget
FOR EACH ROW
EXECUTE PROCEDURE research_os_reject_mutation();

CREATE TRIGGER trg_audit_event_append_only
BEFORE UPDATE OR DELETE ON audit_event
FOR EACH ROW
EXECUTE PROCEDURE research_os_reject_mutation();
"""


def upgrade() -> None:
    op.create_table(
        "program",
        sa.Column("program_id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("program_id"),
    )
    op.create_table(
        "authorization_source",
        sa.Column("authorization_source_id", sa.Text(), nullable=False),
        sa.Column("program_id", sa.Text(), nullable=False),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("provenance_reference", sa.Text(), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["program_id"], ["program.program_id"]),
        sa.PrimaryKeyConstraint("authorization_source_id"),
        sa.UniqueConstraint(
            "authorization_source_id",
            "program_id",
            name="uq_authorization_source_id_program",
        ),
        sa.CheckConstraint(
            "state IN ('ACTIVE', 'EXPIRED', 'REVOKED')",
            name="ck_authorization_source_state",
        ),
        sa.CheckConstraint(
            "effective_until IS NULL OR effective_from IS NULL "
            "OR effective_until >= effective_from",
            name="ck_authorization_source_effective_window",
        ),
    )
    op.create_table(
        "research_run",
        sa.Column("research_run_id", sa.Text(), nullable=False),
        sa.Column("program_id", sa.Text(), nullable=False),
        sa.Column("authorization_source_id", sa.Text(), nullable=False),
        sa.Column("initiated_by_actor_id", sa.Text(), nullable=False),
        sa.Column("initiated_by_actor_type", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["program_id"], ["program.program_id"]),
        sa.ForeignKeyConstraint(
            ["authorization_source_id", "program_id"],
            [
                "authorization_source.authorization_source_id",
                "authorization_source.program_id",
            ],
            name="fk_research_run_authorization_same_program",
        ),
        sa.PrimaryKeyConstraint("research_run_id"),
        sa.CheckConstraint(
            "initiated_by_actor_type IN "
            "('HUMAN_OPERATOR', 'CONTROL_PLANE', 'WORKER', 'INTEGRATION')",
            name="ck_research_run_actor_type",
        ),
    )
    op.create_table(
        "issued_budget",
        sa.Column("budget_id", sa.Text(), nullable=False),
        sa.Column("research_run_id", sa.Text(), nullable=False),
        sa.Column("max_requests", sa.Integer(), nullable=False),
        sa.Column("max_tool_calls", sa.Integer(), nullable=False),
        sa.Column("max_runtime_ms", sa.Integer(), nullable=False),
        sa.Column("max_concurrency", sa.Integer(), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["research_run_id"], ["research_run.research_run_id"]),
        sa.PrimaryKeyConstraint("budget_id"),
        sa.UniqueConstraint(
            "budget_id", "research_run_id", name="uq_issued_budget_id_run"
        ),
        sa.CheckConstraint("max_requests >= 0", name="ck_issued_budget_max_requests"),
        sa.CheckConstraint("max_tool_calls >= 0", name="ck_issued_budget_max_tool_calls"),
        sa.CheckConstraint(
            "max_runtime_ms >= 0", name="ck_issued_budget_max_runtime_ms"
        ),
        sa.CheckConstraint(
            "max_concurrency >= 0", name="ck_issued_budget_max_concurrency"
        ),
    )
    op.create_table(
        "hypothesis",
        sa.Column("hypothesis_id", sa.Text(), nullable=False),
        sa.Column("research_run_id", sa.Text(), nullable=False),
        sa.Column("claim", sa.Text(), nullable=False),
        sa.Column("origin_reference", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["research_run_id"], ["research_run.research_run_id"]),
        sa.PrimaryKeyConstraint("hypothesis_id"),
        sa.UniqueConstraint(
            "hypothesis_id", "research_run_id", name="uq_hypothesis_id_run"
        ),
    )
    op.create_table(
        "experiment",
        sa.Column("experiment_id", sa.Text(), nullable=False),
        sa.Column("research_run_id", sa.Text(), nullable=False),
        sa.Column("hypothesis_id", sa.Text(), nullable=False),
        sa.Column("budget_id", sa.Text(), nullable=False),
        sa.Column("execution_state", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["hypothesis_id", "research_run_id"],
            ["hypothesis.hypothesis_id", "hypothesis.research_run_id"],
            name="fk_experiment_hypothesis_same_run",
        ),
        sa.ForeignKeyConstraint(
            ["budget_id", "research_run_id"],
            ["issued_budget.budget_id", "issued_budget.research_run_id"],
            name="fk_experiment_budget_same_run",
        ),
        sa.PrimaryKeyConstraint("experiment_id"),
        sa.CheckConstraint(
            "execution_state IN ("
            "'PLANNED', 'AUTHORIZATION_CHECK', 'READY', 'RUNNING', "
            "'EXECUTION_SUCCEEDED', 'EXECUTION_FAILED', 'BLOCKED', "
            "'CANCELLED', 'BUDGET_EXHAUSTED')",
            name="ck_experiment_execution_state",
        ),
    )
    op.create_table(
        "worker_result",
        sa.Column("worker_result_id", sa.Text(), nullable=False),
        sa.Column("experiment_id", sa.Text(), nullable=False),
        sa.Column("contract_version", sa.Text(), nullable=False),
        sa.Column("worker_id", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("correlation_id", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "raw_artifact_descriptors",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("diagnostics", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "control_signal", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiment.experiment_id"]),
        sa.PrimaryKeyConstraint("worker_result_id"),
        sa.CheckConstraint(
            "status IN ("
            "'SUCCEEDED', 'EXECUTION_FAILED', 'BLOCKED', 'CANCELLED', "
            "'TIMED_OUT', 'BUDGET_EXHAUSTED', 'REAUTHORIZATION_REQUIRED')",
            name="ck_worker_result_status",
        ),
    )
    op.create_table(
        "observation",
        sa.Column("observation_id", sa.Text(), nullable=False),
        sa.Column("worker_result_id", sa.Text(), nullable=False),
        sa.Column("observation_kind", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("normalization_version", sa.Text(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["worker_result_id"], ["worker_result.worker_result_id"]
        ),
        sa.PrimaryKeyConstraint("observation_id"),
    )
    op.create_table(
        "audit_event",
        sa.Column("audit_event_id", sa.Text(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_id", sa.Text(), nullable=False),
        sa.Column("actor_type", sa.Text(), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("subject_type", sa.Text(), nullable=False),
        sa.Column("subject_id", sa.Text(), nullable=False),
        sa.Column("correlation_id", sa.Text(), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint("audit_event_id"),
        sa.CheckConstraint(
            "actor_type IN "
            "('HUMAN_OPERATOR', 'CONTROL_PLANE', 'WORKER', 'INTEGRATION')",
            name="ck_audit_event_actor_type",
        ),
    )
    op.execute(sa.text(APPEND_ONLY_SQL))


def downgrade() -> None:
    op.execute(
        sa.text(
            "DROP TRIGGER IF EXISTS trg_audit_event_append_only ON audit_event;"
            "DROP TRIGGER IF EXISTS trg_issued_budget_append_only ON issued_budget;"
            "DROP FUNCTION IF EXISTS research_os_reject_mutation();"
        )
    )
    op.drop_table("audit_event")
    op.drop_table("observation")
    op.drop_table("worker_result")
    op.drop_table("experiment")
    op.drop_table("hypothesis")
    op.drop_table("issued_budget")
    op.drop_table("research_run")
    op.drop_table("authorization_source")
    op.drop_table("program")
