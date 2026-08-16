"""Exploration policy and temporal snapshot/change records (Decisions 043–044 / GATE 09).

Revision ID: a15_001_exploration_temporal
Revises: a14_001_invariant_chain
Create Date: 2026-08-17

Does not rewrite a3–a14.
Selection is not authorization. Change is not a vulnerability.
Snapshot retention/compaction is deferred and must never delete Evidence provenance.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a15_001_exploration_temporal"
down_revision: Union[str, Sequence[str], None] = "a14_001_invariant_chain"
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
        "research_opportunity",
        sa.Column("opportunity_id", sa.Text(), primary_key=True),
        sa.Column("research_run_id", sa.Text(), nullable=False),
        sa.Column("opportunity_kind", sa.Text(), nullable=False),
        sa.Column("mode", sa.Text(), nullable=False),
        sa.Column("source_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("proposed_direction", sa.Text(), nullable=False),
        sa.Column("unresolved_question", sa.Text(), nullable=False),
        sa.Column("expected_information_value_description", sa.Text(), nullable=False),
        sa.Column("assumptions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("dimensions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("context_signature", sa.Text(), nullable=False),
        sa.Column("novelty_composition_marker", sa.Boolean(), nullable=False),
        sa.Column("prior_attempt_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("structural_identity", sa.Text(), nullable=False),
        sa.Column("strategy_version", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["research_run_id"],
            ["research_run.research_run_id"],
            name="fk_research_opportunity_research_run",
        ),
        sa.CheckConstraint(
            "mode IN ('EXPLORATION', 'EXPLOITATION')",
            name="ck_research_opportunity_mode",
        ),
        sa.UniqueConstraint(
            "research_run_id",
            "structural_identity",
            name="uq_research_opportunity_run_identity",
        ),
    )
    op.execute(
        sa.text(
            APPEND_ONLY_TRIGGER.format(
                name="trg_research_opportunity_append_only", table="research_opportunity"
            )
        )
    )
    op.create_table(
        "research_selection",
        sa.Column("selection_id", sa.Text(), primary_key=True),
        sa.Column("research_run_id", sa.Text(), nullable=False),
        sa.Column("opportunity_id", sa.Text(), nullable=False),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.Column("reason_codes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("structural_identity", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["research_run_id"],
            ["research_run.research_run_id"],
            name="fk_research_selection_research_run",
        ),
        sa.CheckConstraint(
            "outcome IN ("
            "'SELECT', 'DEFER', 'SKIP_DUPLICATE', 'SKIP_LOW_INFORMATION', "
            "'BLOCKED_BUDGET', 'BLOCKED_POLICY', 'NEEDS_MORE_CONTEXT')",
            name="ck_research_selection_outcome",
        ),
    )
    op.execute(
        sa.text(
            APPEND_ONLY_TRIGGER.format(
                name="trg_research_selection_append_only", table="research_selection"
            )
        )
    )
    op.create_table(
        "snapshot",
        sa.Column("snapshot_id", sa.Text(), primary_key=True),
        sa.Column("research_run_id", sa.Text(), nullable=False),
        sa.Column("program_id", sa.Text(), nullable=False),
        sa.Column("target_identity", sa.Text(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("strategy_version", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["research_run_id"],
            ["research_run.research_run_id"],
            name="fk_snapshot_research_run",
        ),
        sa.ForeignKeyConstraint(
            ["program_id"],
            ["program.program_id"],
            name="fk_snapshot_program",
        ),
    )
    op.execute(
        sa.text(APPEND_ONLY_TRIGGER.format(name="trg_snapshot_append_only", table="snapshot"))
    )
    op.create_table(
        "snapshot_member",
        sa.Column("snapshot_id", sa.Text(), primary_key=True),
        sa.Column("observation_id", sa.Text(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["snapshot.snapshot_id"],
            name="fk_snapshot_member_snapshot",
        ),
        sa.ForeignKeyConstraint(
            ["observation_id"],
            ["observation.observation_id"],
            name="fk_snapshot_member_observation",
        ),
    )
    op.execute(
        sa.text(
            APPEND_ONLY_TRIGGER.format(
                name="trg_snapshot_member_append_only", table="snapshot_member"
            )
        )
    )
    op.create_table(
        "change_event",
        sa.Column("change_event_id", sa.Text(), primary_key=True),
        sa.Column("research_run_id", sa.Text(), nullable=False),
        sa.Column("baseline_snapshot_id", sa.Text(), nullable=False),
        sa.Column("variant_snapshot_id", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("source_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("strategy_version", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["research_run_id"],
            ["research_run.research_run_id"],
            name="fk_change_event_research_run",
        ),
        sa.ForeignKeyConstraint(
            ["baseline_snapshot_id"],
            ["snapshot.snapshot_id"],
            name="fk_change_event_baseline_snapshot",
        ),
        sa.ForeignKeyConstraint(
            ["variant_snapshot_id"],
            ["snapshot.snapshot_id"],
            name="fk_change_event_variant_snapshot",
        ),
        sa.CheckConstraint(
            "category IN ("
            "'ADDED', 'REMOVED', 'MODIFIED', 'RELATION_CHANGED', "
            "'STATE_CHANGED', 'BEHAVIOR_CHANGED', 'UNKNOWN_CHANGE')",
            name="ck_change_event_category",
        ),
    )
    op.execute(
        sa.text(
            APPEND_ONLY_TRIGGER.format(
                name="trg_change_event_append_only", table="change_event"
            )
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP TRIGGER IF EXISTS trg_change_event_append_only ON change_event"))
    op.drop_table("change_event")
    op.execute(
        sa.text("DROP TRIGGER IF EXISTS trg_snapshot_member_append_only ON snapshot_member")
    )
    op.drop_table("snapshot_member")
    op.execute(sa.text("DROP TRIGGER IF EXISTS trg_snapshot_append_only ON snapshot"))
    op.drop_table("snapshot")
    op.execute(
        sa.text("DROP TRIGGER IF EXISTS trg_research_selection_append_only ON research_selection")
    )
    op.drop_table("research_selection")
    op.execute(
        sa.text(
            "DROP TRIGGER IF EXISTS trg_research_opportunity_append_only ON research_opportunity"
        )
    )
    op.drop_table("research_opportunity")
