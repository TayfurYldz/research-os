"""Target inference and differential observation records (Decisions 039–040 / GATE 07).

Revision ID: a13_001_target_differential
Revises: a12_001_finding_acceptance
Create Date: 2026-08-17

Does not rewrite a3–a12.
Target inference is not Observation. Differential result is not Evidence.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a13_001_target_differential"
down_revision: Union[str, Sequence[str], None] = "a12_001_finding_acceptance"
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
        "target_inference",
        sa.Column("inference_id", sa.Text(), primary_key=True),
        sa.Column("research_run_id", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("epistemic_status", sa.Text(), nullable=False),
        sa.Column("opaque_ref", sa.Text(), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("source_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("attributes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("strategy_version", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["research_run_id"],
            ["research_run.research_run_id"],
            name="fk_target_inference_research_run",
        ),
        sa.CheckConstraint(
            "epistemic_status IN ('INFERRED', 'HYPOTHESIZED')",
            name="ck_target_inference_epistemic_status",
        ),
        sa.CheckConstraint(
            "kind IN ('ACTOR', 'ROLE', 'SESSION', 'RESOURCE', 'ACTION', 'STATE', "
            "'RELATIONSHIP', 'STATE_TRANSITION')",
            name="ck_target_inference_kind",
        ),
    )
    op.execute(
        sa.text(
            APPEND_ONLY_TRIGGER.format(
                name="trg_target_inference_append_only", table="target_inference"
            )
        )
    )

    op.create_table(
        "differential_observation",
        sa.Column("differential_id", sa.Text(), primary_key=True),
        sa.Column("research_run_id", sa.Text(), nullable=False),
        sa.Column("case_id", sa.Text(), nullable=False),
        sa.Column(
            "baseline_observation_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "variant_observation_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "changed_dimensions", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "common_dimensions", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "observed_differences", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "observed_similarities",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("interpretation", sa.Text(), nullable=False),
        sa.Column("source_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("strategy_version", sa.Text(), nullable=False),
        sa.Column(
            "alternative_explanation_slots",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["research_run_id"],
            ["research_run.research_run_id"],
            name="fk_differential_observation_research_run",
        ),
        sa.CheckConstraint(
            "interpretation IN ('CONTROLLED_DIFFERENCE', 'EQUIVALENT', 'INCOMPARABLE')",
            name="ck_differential_interpretation",
        ),
    )
    op.execute(
        sa.text(
            APPEND_ONLY_TRIGGER.format(
                name="trg_differential_observation_append_only",
                table="differential_observation",
            )
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DROP TRIGGER IF EXISTS trg_differential_observation_append_only "
            "ON differential_observation"
        )
    )
    op.drop_table("differential_observation")
    op.execute(
        sa.text("DROP TRIGGER IF EXISTS trg_target_inference_append_only ON target_inference")
    )
    op.drop_table("target_inference")
