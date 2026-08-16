"""Transition A provenance and ingestion identity.

Revision ID: a6_001_transition_a_provenance
Revises: a3_001_persistence_spine
Create Date: 2026-08-16

Adds first-class WorkerResult request-envelope columns, request_id uniqueness,
and Observation (worker_result, kind, normalizer version) uniqueness.

Does not rewrite a3_001_persistence_spine. Does not add Evidence/Candidate/Finding.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a6_001_transition_a_provenance"
down_revision: Union[str, Sequence[str], None] = "a3_001_persistence_spine"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_experiment_id_run",
        "experiment",
        ["experiment_id", "research_run_id"],
    )
    op.add_column(
        "worker_result",
        sa.Column("research_run_id", sa.Text(), nullable=False),
    )
    op.add_column(
        "worker_result",
        sa.Column("request_id", sa.Text(), nullable=False),
    )
    op.add_column(
        "worker_result",
        sa.Column("parent_request_id", sa.Text(), nullable=True),
    )
    op.add_column(
        "worker_result",
        sa.Column("worker_capability", sa.Text(), nullable=False),
    )
    op.add_column(
        "worker_result",
        sa.Column("action", sa.Text(), nullable=False),
    )
    op.add_column(
        "worker_result",
        sa.Column("authorization_decision_reference", sa.Text(), nullable=False),
    )
    op.add_column(
        "worker_result",
        sa.Column("budget_id", sa.Text(), nullable=False),
    )
    op.add_column(
        "worker_result",
        sa.Column("side_effect_level", sa.Integer(), nullable=False),
    )
    op.alter_column(
        "worker_result",
        "correlation_id",
        existing_type=sa.Text(),
        nullable=False,
    )
    op.drop_constraint(
        "worker_result_experiment_id_fkey",
        "worker_result",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_worker_result_experiment_same_run",
        "worker_result",
        "experiment",
        ["experiment_id", "research_run_id"],
        ["experiment_id", "research_run_id"],
    )
    op.create_foreign_key(
        "fk_worker_result_budget_same_run",
        "worker_result",
        "issued_budget",
        ["budget_id", "research_run_id"],
        ["budget_id", "research_run_id"],
    )
    op.create_unique_constraint(
        "uq_worker_result_request_id",
        "worker_result",
        ["request_id"],
    )
    op.create_check_constraint(
        "ck_worker_result_side_effect_level",
        "worker_result",
        "side_effect_level IN (0, 1, 2, 3)",
    )
    op.create_unique_constraint(
        "uq_observation_result_kind_version",
        "observation",
        ["worker_result_id", "observation_kind", "normalization_version"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_observation_result_kind_version",
        "observation",
        type_="unique",
    )
    op.drop_constraint(
        "ck_worker_result_side_effect_level",
        "worker_result",
        type_="check",
    )
    op.drop_constraint(
        "uq_worker_result_request_id",
        "worker_result",
        type_="unique",
    )
    op.drop_constraint(
        "fk_worker_result_budget_same_run",
        "worker_result",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_worker_result_experiment_same_run",
        "worker_result",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "worker_result_experiment_id_fkey",
        "worker_result",
        "experiment",
        ["experiment_id"],
        ["experiment_id"],
    )
    op.alter_column(
        "worker_result",
        "correlation_id",
        existing_type=sa.Text(),
        nullable=True,
    )
    op.drop_column("worker_result", "side_effect_level")
    op.drop_column("worker_result", "budget_id")
    op.drop_column("worker_result", "authorization_decision_reference")
    op.drop_column("worker_result", "action")
    op.drop_column("worker_result", "worker_capability")
    op.drop_column("worker_result", "parent_request_id")
    op.drop_column("worker_result", "request_id")
    op.drop_column("worker_result", "research_run_id")
    op.drop_constraint("uq_experiment_id_run", "experiment", type_="unique")
