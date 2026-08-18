"""Durable GATE 22 discovery surface. Append-only after a21 session context.

Revision ID: a22_001_discovery_surface
Revises: a21_001_session_context
Create Date: 2026-08-18

Attack surface graph is not persisted as node/edge tables.
ControlEvent is not Observation. DiscoveryFact OBSERVED|DERIVED only.
Inference cannot become OBSERVED. FrontierItem is not authorization.
Projection receipts are the correctness ledger; watermarks are not.
alembic_version.version_num is VARCHAR(32); keep revision ids within that bound.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a22_001_discovery_surface"
down_revision: Union[str, Sequence[str], None] = "a21_001_session_context"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FACT_KINDS = (
    "ORIGIN",
    "EXACT_PATH",
    "HTTP_OPERATION",
    "PAGE_STATE",
    "CONTROL",
    "FORM",
    "RESPONSE_SHAPE",
    "RESOURCE_INSTANCE_CANDIDATE",
    "WORKFLOW_STATE",
    "WORKFLOW_TRANSITION",
    "SCOPE_BOUNDARY_CANDIDATE",
)
CONTROL_KINDS = (
    "REAUTHORIZATION_REQUIRED",
    "REDIRECT_BOUNDARY",
    "POPUP_BOUNDARY",
    "NEW_ORIGIN_BOUNDARY",
    "IFRAME_BOUNDARY",
)
INFERENCE_KINDS = ("ROUTE_TEMPLATE", "OBJECT_TYPE", "OBJECT_INSTANCE", "SAME_AS")
GOAL_KINDS = (
    "INSPECT_PATH",
    "INSPECT_CONTROL",
    "CHARACTERIZE_HTTP_OPERATION",
    "OBSERVE_UNDER_IDENTITY",
    "RESOLVE_TRANSITION_RESULT",
    "RESOLVE_OBJECT_TYPE",
    "INSPECT_SPA_PATH",
)
FRONTIER_EVENTS = (
    "CREATED",
    "ELIGIBLE",
    "SELECTED",
    "BLOCKED_SCOPE",
    "BLOCKED_AUTH",
    "BLOCKED_BUDGET",
    "AWAITING_REAUTHORIZATION",
    "NO_NEW_INFORMATION",
    "OBSERVED",
    "FAILED_TRANSIENT",
    "FAILED_TERMINAL",
    "SUPERSEDED",
)
ONE_PRIMARY = (
    "(CASE WHEN {a} IS NOT NULL THEN 1 ELSE 0 END + "
    "CASE WHEN {b} IS NOT NULL THEN 1 ELSE 0 END + "
    "CASE WHEN {c} IS NOT NULL THEN 1 ELSE 0 END + "
    "CASE WHEN {d} IS NOT NULL THEN 1 ELSE 0 END) = 1"
)


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_worker_result_id_run",
        "worker_result",
        ["worker_result_id", "research_run_id"],
    )
    op.create_unique_constraint(
        "uq_execution_attempt_id_run",
        "execution_attempt",
        ["attempt_id", "research_run_id"],
    )

    op.create_table(
        "discovery_run_config",
        sa.Column("research_run_id", sa.Text(), nullable=False),
        sa.Column("strategy_version", sa.Text(), nullable=False),
        sa.Column("seed_target_reference", sa.Text(), nullable=False),
        sa.Column("normalized_origin", sa.Text(), nullable=False),
        sa.Column("normalized_path", sa.Text(), nullable=False),
        sa.Column("max_discovery_cycles", sa.Integer(), nullable=False),
        sa.Column("max_frontier_items", sa.Integer(), nullable=False),
        sa.Column("max_new_facts_per_cycle", sa.Integer(), nullable=False),
        sa.Column("max_browser_actions", sa.Integer(), nullable=False),
        sa.Column("max_http_transactions", sa.Integer(), nullable=False),
        sa.Column("max_per_route_revisit", sa.Integer(), nullable=False),
        sa.Column("max_identity_variants", sa.Integer(), nullable=False),
        sa.Column("max_transition_depth", sa.Integer(), nullable=False),
        sa.Column("max_graph_depth_from_seed", sa.Integer(), nullable=False),
        sa.Column("max_template_inference_fanout", sa.Integer(), nullable=False),
        sa.Column("max_duplicate_observations", sa.Integer(), nullable=False),
        sa.Column("configuration_fingerprint", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["research_run_id"], ["research_run.research_run_id"]),
        sa.PrimaryKeyConstraint("research_run_id"),
        sa.CheckConstraint(
            "strategy_version = 'surface.discovery.v1'",
            name="ck_discovery_run_config_strategy",
        ),
        sa.CheckConstraint(
            "max_discovery_cycles >= 0 AND max_frontier_items >= 0 AND "
            "max_new_facts_per_cycle >= 0 AND max_browser_actions >= 0 AND "
            "max_http_transactions >= 0 AND max_per_route_revisit >= 0 AND "
            "max_identity_variants >= 0 AND max_transition_depth >= 0 AND "
            "max_graph_depth_from_seed >= 0 AND max_template_inference_fanout >= 0 AND "
            "max_duplicate_observations >= 0",
            name="ck_discovery_run_config_bounds",
        ),
    )

    op.create_table(
        "control_event",
        sa.Column("control_event_id", sa.Text(), nullable=False),
        sa.Column("research_run_id", sa.Text(), nullable=False),
        sa.Column("event_kind", sa.Text(), nullable=False),
        sa.Column("worker_result_id", sa.Text(), nullable=False),
        sa.Column("identity_id", sa.Text(), nullable=False),
        sa.Column("target_reference", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("session_context_id", sa.Text(), nullable=True),
        sa.Column("channel", sa.Text(), nullable=True),
        sa.Column("location_origin", sa.Text(), nullable=True),
        sa.Column("location_path", sa.Text(), nullable=True),
        sa.Column("request_id", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["research_run_id"], ["research_run.research_run_id"]),
        sa.ForeignKeyConstraint(
            ["worker_result_id", "research_run_id"],
            ["worker_result.worker_result_id", "worker_result.research_run_id"],
            name="fk_control_event_worker_result_same_run",
        ),
        sa.PrimaryKeyConstraint("control_event_id"),
        sa.UniqueConstraint("control_event_id", "research_run_id", name="uq_control_event_id_run"),
        sa.UniqueConstraint("worker_result_id", name="uq_control_event_worker_result"),
        sa.CheckConstraint(
            "event_kind IN (" + ", ".join(f"'{item}'" for item in CONTROL_KINDS) + ")",
            name="ck_control_event_kind",
        ),
    )

    op.create_table(
        "discovery_fact",
        sa.Column("fact_id", sa.Text(), nullable=False),
        sa.Column("research_run_id", sa.Text(), nullable=False),
        sa.Column("fact_kind", sa.Text(), nullable=False),
        sa.Column("canonical_key", sa.Text(), nullable=False),
        sa.Column("epistemic_status", sa.Text(), nullable=False),
        sa.Column("identity_id", sa.Text(), nullable=False),
        sa.Column("target_reference", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("session_context_id", sa.Text(), nullable=True),
        sa.Column("normalized_origin", sa.Text(), nullable=True),
        sa.Column("normalized_path", sa.Text(), nullable=True),
        sa.Column("http_method", sa.Text(), nullable=True),
        sa.Column("attributes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["research_run_id"], ["research_run.research_run_id"]),
        sa.PrimaryKeyConstraint("fact_id"),
        sa.UniqueConstraint("fact_id", "research_run_id", name="uq_discovery_fact_id_run"),
        sa.UniqueConstraint("research_run_id", "canonical_key", name="uq_discovery_fact_canonical"),
        sa.CheckConstraint(
            "fact_kind IN (" + ", ".join(f"'{item}'" for item in FACT_KINDS) + ")",
            name="ck_discovery_fact_kind",
        ),
        sa.CheckConstraint(
            "epistemic_status IN ('OBSERVED', 'DERIVED')",
            name="ck_discovery_fact_epistemic",
        ),
        sa.CheckConstraint(
            "fact_kind <> 'SCOPE_BOUNDARY_CANDIDATE' OR epistemic_status = 'DERIVED'",
            name="ck_discovery_fact_boundary_derived",
        ),
    )

    op.create_table(
        "discovery_inference",
        sa.Column("inference_id", sa.Text(), nullable=False),
        sa.Column("research_run_id", sa.Text(), nullable=False),
        sa.Column("inference_kind", sa.Text(), nullable=False),
        sa.Column("canonical_key", sa.Text(), nullable=False),
        sa.Column("epistemic_status", sa.Text(), nullable=False),
        sa.Column("identity_id", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attributes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["research_run_id"], ["research_run.research_run_id"]),
        sa.PrimaryKeyConstraint("inference_id"),
        sa.UniqueConstraint("inference_id", "research_run_id", name="uq_discovery_inference_id_run"),
        sa.UniqueConstraint(
            "research_run_id", "canonical_key", name="uq_discovery_inference_canonical"
        ),
        sa.CheckConstraint(
            "inference_kind IN (" + ", ".join(f"'{item}'" for item in INFERENCE_KINDS) + ")",
            name="ck_discovery_inference_kind",
        ),
        sa.CheckConstraint(
            "epistemic_status IN ('INFERRED', 'HYPOTHESIZED')",
            name="ck_discovery_inference_epistemic",
        ),
    )

    op.create_table(
        "discovery_inference_source",
        sa.Column("source_row_id", sa.Text(), nullable=False),
        sa.Column("research_run_id", sa.Text(), nullable=False),
        sa.Column("inference_id", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("observation_id", sa.Text(), nullable=True),
        sa.Column("control_event_id", sa.Text(), nullable=True),
        sa.Column("source_fact_id", sa.Text(), nullable=True),
        sa.Column("source_inference_id", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["inference_id", "research_run_id"],
            ["discovery_inference.inference_id", "discovery_inference.research_run_id"],
            name="fk_discovery_inference_source_parent",
        ),
        sa.ForeignKeyConstraint(["observation_id"], ["observation.observation_id"]),
        sa.ForeignKeyConstraint(
            ["control_event_id", "research_run_id"],
            ["control_event.control_event_id", "control_event.research_run_id"],
            name="fk_discovery_inference_source_control",
        ),
        sa.ForeignKeyConstraint(
            ["source_fact_id", "research_run_id"],
            ["discovery_fact.fact_id", "discovery_fact.research_run_id"],
            name="fk_discovery_inference_source_fact",
        ),
        sa.ForeignKeyConstraint(
            ["source_inference_id", "research_run_id"],
            ["discovery_inference.inference_id", "discovery_inference.research_run_id"],
            name="fk_discovery_inference_source_inference",
        ),
        sa.PrimaryKeyConstraint("source_row_id"),
        sa.CheckConstraint(
            ONE_PRIMARY.format(
                a="observation_id",
                b="control_event_id",
                c="source_fact_id",
                d="source_inference_id",
            ),
            name="ck_discovery_inference_source_one_primary",
        ),
    )
    op.create_index(
        "uq_discovery_inference_source_obs",
        "discovery_inference_source",
        ["inference_id", "observation_id"],
        unique=True,
        postgresql_where=sa.text("observation_id IS NOT NULL"),
    )
    op.create_index(
        "uq_discovery_inference_source_fact",
        "discovery_inference_source",
        ["inference_id", "source_fact_id"],
        unique=True,
        postgresql_where=sa.text("source_fact_id IS NOT NULL"),
    )

    op.create_table(
        "discovery_fact_source",
        sa.Column("source_row_id", sa.Text(), nullable=False),
        sa.Column("research_run_id", sa.Text(), nullable=False),
        sa.Column("fact_id", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("observation_id", sa.Text(), nullable=True),
        sa.Column("control_event_id", sa.Text(), nullable=True),
        sa.Column("source_fact_id", sa.Text(), nullable=True),
        sa.Column("source_inference_id", sa.Text(), nullable=True),
        sa.Column("worker_result_id", sa.Text(), nullable=True),
        sa.Column("execution_attempt_id", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["fact_id", "research_run_id"],
            ["discovery_fact.fact_id", "discovery_fact.research_run_id"],
            name="fk_discovery_fact_source_parent",
        ),
        sa.ForeignKeyConstraint(["observation_id"], ["observation.observation_id"]),
        sa.ForeignKeyConstraint(
            ["control_event_id", "research_run_id"],
            ["control_event.control_event_id", "control_event.research_run_id"],
            name="fk_discovery_fact_source_control",
        ),
        sa.ForeignKeyConstraint(
            ["source_fact_id", "research_run_id"],
            ["discovery_fact.fact_id", "discovery_fact.research_run_id"],
            name="fk_discovery_fact_source_fact",
        ),
        sa.ForeignKeyConstraint(
            ["source_inference_id", "research_run_id"],
            ["discovery_inference.inference_id", "discovery_inference.research_run_id"],
            name="fk_discovery_fact_source_inference",
        ),
        sa.PrimaryKeyConstraint("source_row_id"),
        sa.CheckConstraint(
            ONE_PRIMARY.format(
                a="observation_id",
                b="control_event_id",
                c="source_fact_id",
                d="source_inference_id",
            ),
            name="ck_discovery_fact_source_one_primary",
        ),
    )
    op.create_index(
        "uq_discovery_fact_source_obs",
        "discovery_fact_source",
        ["fact_id", "observation_id"],
        unique=True,
        postgresql_where=sa.text("observation_id IS NOT NULL"),
    )
    op.create_index(
        "uq_discovery_fact_source_control",
        "discovery_fact_source",
        ["fact_id", "control_event_id"],
        unique=True,
        postgresql_where=sa.text("control_event_id IS NOT NULL"),
    )

    op.create_table(
        "frontier_item",
        sa.Column("frontier_id", sa.Text(), nullable=False),
        sa.Column("research_run_id", sa.Text(), nullable=False),
        sa.Column("strategy_version", sa.Text(), nullable=False),
        sa.Column("goal_kind", sa.Text(), nullable=False),
        sa.Column("candidate_origin", sa.Text(), nullable=False),
        sa.Column("candidate_path", sa.Text(), nullable=False),
        sa.Column("identity_id", sa.Text(), nullable=False),
        sa.Column("proposed_capability", sa.Text(), nullable=False),
        sa.Column("proposed_action", sa.Text(), nullable=False),
        sa.Column("expected_side_effect", sa.Integer(), nullable=False),
        sa.Column("budget_class", sa.Integer(), nullable=False),
        sa.Column("structural_signature", sa.Text(), nullable=False),
        sa.Column("dedupe_identity", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("session_context_id", sa.Text(), nullable=True),
        sa.Column("scope_hint", sa.Text(), nullable=True),
        sa.Column("attributes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("current_state", sa.Text(), nullable=True),
        sa.Column("state_version", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["research_run_id"], ["research_run.research_run_id"]),
        sa.PrimaryKeyConstraint("frontier_id"),
        sa.UniqueConstraint("frontier_id", "research_run_id", name="uq_frontier_item_id_run"),
        sa.UniqueConstraint("research_run_id", "dedupe_identity", name="uq_frontier_item_dedupe"),
        sa.CheckConstraint(
            "strategy_version = 'surface.discovery.v1'",
            name="ck_frontier_item_strategy",
        ),
        sa.CheckConstraint(
            "goal_kind IN (" + ", ".join(f"'{item}'" for item in GOAL_KINDS) + ")",
            name="ck_frontier_item_goal",
        ),
        sa.CheckConstraint(
            "expected_side_effect IN (0, 1, 2, 3) AND budget_class IN (0, 1, 2, 3)",
            name="ck_frontier_item_side_effect",
        ),
        sa.CheckConstraint(
            "structural_signature NOT LIKE 'el-%'",
            name="ck_frontier_item_no_ephemeral_ref",
        ),
    )

    op.create_table(
        "frontier_source",
        sa.Column("source_row_id", sa.Text(), nullable=False),
        sa.Column("research_run_id", sa.Text(), nullable=False),
        sa.Column("frontier_id", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("seed_config_run_id", sa.Text(), nullable=True),
        sa.Column("source_fact_id", sa.Text(), nullable=True),
        sa.Column("source_inference_id", sa.Text(), nullable=True),
        sa.Column("control_event_id", sa.Text(), nullable=True),
        sa.Column("observation_id", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["frontier_id", "research_run_id"],
            ["frontier_item.frontier_id", "frontier_item.research_run_id"],
            name="fk_frontier_source_item",
        ),
        sa.ForeignKeyConstraint(
            ["seed_config_run_id"],
            ["discovery_run_config.research_run_id"],
            name="fk_frontier_source_seed",
        ),
        sa.ForeignKeyConstraint(
            ["source_fact_id", "research_run_id"],
            ["discovery_fact.fact_id", "discovery_fact.research_run_id"],
            name="fk_frontier_source_fact",
        ),
        sa.ForeignKeyConstraint(
            ["source_inference_id", "research_run_id"],
            ["discovery_inference.inference_id", "discovery_inference.research_run_id"],
            name="fk_frontier_source_inference",
        ),
        sa.ForeignKeyConstraint(
            ["control_event_id", "research_run_id"],
            ["control_event.control_event_id", "control_event.research_run_id"],
            name="fk_frontier_source_control",
        ),
        sa.ForeignKeyConstraint(["observation_id"], ["observation.observation_id"]),
        sa.PrimaryKeyConstraint("source_row_id"),
        sa.CheckConstraint(
            "("
            "CASE WHEN seed_config_run_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN source_fact_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN source_inference_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN control_event_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN observation_id IS NOT NULL THEN 1 ELSE 0 END"
            ") = 1",
            name="ck_frontier_source_one_primary",
        ),
        sa.CheckConstraint(
            "seed_config_run_id IS NULL OR seed_config_run_id = research_run_id",
            name="ck_frontier_source_seed_same_run",
        ),
    )

    op.create_table(
        "frontier_event",
        sa.Column("event_id", sa.Text(), nullable=False),
        sa.Column("frontier_id", sa.Text(), nullable=False),
        sa.Column("research_run_id", sa.Text(), nullable=False),
        sa.Column("event_kind", sa.Text(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("selection_generation", sa.Integer(), nullable=True),
        sa.Column("execution_attempt_id", sa.Text(), nullable=True),
        sa.Column("reason_code", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["frontier_id", "research_run_id"],
            ["frontier_item.frontier_id", "frontier_item.research_run_id"],
            name="fk_frontier_event_item",
        ),
        sa.ForeignKeyConstraint(
            ["execution_attempt_id", "research_run_id"],
            ["execution_attempt.attempt_id", "execution_attempt.research_run_id"],
            name="fk_frontier_event_attempt_same_run",
        ),
        sa.PrimaryKeyConstraint("event_id"),
        sa.UniqueConstraint("frontier_id", "sequence", name="uq_frontier_event_sequence"),
        sa.CheckConstraint(
            "event_kind IN (" + ", ".join(f"'{item}'" for item in FRONTIER_EVENTS) + ")",
            name="ck_frontier_event_kind",
        ),
        sa.CheckConstraint("sequence >= 1", name="ck_frontier_event_sequence"),
        sa.CheckConstraint(
            "event_kind <> 'SELECTED' OR selection_generation >= 1",
            name="ck_frontier_event_selected_generation",
        ),
    )
    op.create_index(
        "uq_frontier_event_selected_generation",
        "frontier_event",
        ["frontier_id", "selection_generation"],
        unique=True,
        postgresql_where=sa.text("event_kind = 'SELECTED'"),
    )

    op.create_table(
        "discovery_projection_receipt",
        sa.Column("receipt_id", sa.Text(), nullable=False),
        sa.Column("research_run_id", sa.Text(), nullable=False),
        sa.Column("strategy_version", sa.Text(), nullable=False),
        sa.Column("source_plane", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("observation_id", sa.Text(), nullable=True),
        sa.Column("control_event_id", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["research_run_id"], ["research_run.research_run_id"]),
        sa.ForeignKeyConstraint(["observation_id"], ["observation.observation_id"]),
        sa.ForeignKeyConstraint(
            ["control_event_id", "research_run_id"],
            ["control_event.control_event_id", "control_event.research_run_id"],
            name="fk_discovery_receipt_control",
        ),
        sa.PrimaryKeyConstraint("receipt_id"),
        sa.CheckConstraint(
            "strategy_version = 'surface.discovery.v1'",
            name="ck_discovery_receipt_strategy",
        ),
        sa.CheckConstraint(
            "("
            "(source_plane = 'OBSERVATION' AND observation_id IS NOT NULL "
            "AND control_event_id IS NULL) OR "
            "(source_plane = 'CONTROL_EVENT' AND control_event_id IS NOT NULL "
            "AND observation_id IS NULL)"
            ")",
            name="ck_discovery_receipt_plane",
        ),
    )
    op.create_index(
        "uq_discovery_receipt_observation",
        "discovery_projection_receipt",
        ["research_run_id", "strategy_version", "source_plane", "observation_id"],
        unique=True,
        postgresql_where=sa.text("observation_id IS NOT NULL"),
    )
    op.create_index(
        "uq_discovery_receipt_control",
        "discovery_projection_receipt",
        ["research_run_id", "strategy_version", "source_plane", "control_event_id"],
        unique=True,
        postgresql_where=sa.text("control_event_id IS NOT NULL"),
    )

    op.execute(
        """
        CREATE FUNCTION research_os_observation_same_run() RETURNS trigger AS $$
        BEGIN
          IF NEW.observation_id IS NOT NULL THEN
            IF NOT EXISTS (
              SELECT 1
              FROM observation o
              JOIN worker_result wr ON wr.worker_result_id = o.worker_result_id
              WHERE o.observation_id = NEW.observation_id
                AND wr.research_run_id = NEW.research_run_id
            ) THEN
              RAISE EXCEPTION 'cross-run observation provenance is not allowed';
            END IF;
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    for table_name in (
        "discovery_fact_source",
        "discovery_inference_source",
        "frontier_source",
        "discovery_projection_receipt",
    ):
        op.execute(
            f"""
            CREATE TRIGGER trg_{table_name}_observation_same_run
            BEFORE INSERT ON {table_name}
            FOR EACH ROW EXECUTE PROCEDURE research_os_observation_same_run();
            """
        )


def downgrade() -> None:
    for table_name in (
        "discovery_projection_receipt",
        "frontier_source",
        "discovery_inference_source",
        "discovery_fact_source",
    ):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table_name}_observation_same_run ON {table_name}")
    op.execute("DROP FUNCTION IF EXISTS research_os_observation_same_run()")
    op.drop_table("discovery_projection_receipt")
    op.drop_table("frontier_event")
    op.drop_table("frontier_source")
    op.drop_table("frontier_item")
    op.drop_table("discovery_fact_source")
    op.drop_table("discovery_inference_source")
    op.drop_table("discovery_inference")
    op.drop_table("discovery_fact")
    op.drop_table("control_event")
    op.drop_table("discovery_run_config")
    op.drop_constraint("uq_execution_attempt_id_run", "execution_attempt", type_="unique")
    op.drop_constraint("uq_worker_result_id_run", "worker_result", type_="unique")
