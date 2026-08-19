"""SD-G4 token economy policy.

Revision ID: a28_001_token_economy
Revises: a27_001_attack_surface_snapshot
Create Date: 2026-08-19

Adds program daily LLM budget and budget_consumption resource_metadata.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a28_001_token_economy"
down_revision: Union[str, Sequence[str], None] = "a27_001_attack_surface_snapshot"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "issued_budget",
        "research_run_id",
        existing_type=sa.Text(),
        existing_nullable=False,
        nullable=True,
    )
    op.add_column(
        "program_policy",
        sa.Column("daily_llm_budget_microdollars", sa.Integer(), nullable=True),
    )
    op.create_check_constraint(
        "ck_program_policy_daily_budget_non_negative",
        "program_policy",
        "daily_llm_budget_microdollars IS NULL OR daily_llm_budget_microdollars >= 0",
    )
    op.add_column(
        "budget_consumption",
        sa.Column("resource_metadata", sa.JSON(), nullable=True),
    )
    op.alter_column(
        "budget_consumption",
        "research_run_id",
        existing_type=sa.Text(),
        existing_nullable=False,
        nullable=True,
    )
    op.create_check_constraint(
        "ck_budget_consumption_resource_type_v2",
        "budget_consumption",
        "resource_type IN ("
        "'MODEL_CALL', 'MODEL_TOKENS_IN', 'MODEL_TOKENS_OUT', 'MODEL_ESCALATION_DECISION', "
        "'WORKER_INVOCATION', 'REQUEST', 'EXECUTION_TIME', 'ARTIFACT_BYTES', 'COST')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_budget_consumption_resource_type_v2", "budget_consumption", type_="check"
    )
    op.drop_column("budget_consumption", "resource_metadata")
    op.alter_column(
        "budget_consumption",
        "research_run_id",
        existing_type=sa.Text(),
        existing_nullable=True,
        nullable=False,
    )
    op.drop_constraint(
        "ck_program_policy_daily_budget_non_negative", "program_policy", type_="check"
    )
    op.drop_column("program_policy", "daily_llm_budget_microdollars")
    op.alter_column(
        "issued_budget",
        "research_run_id",
        existing_type=sa.Text(),
        existing_nullable=True,
        nullable=False,
    )
