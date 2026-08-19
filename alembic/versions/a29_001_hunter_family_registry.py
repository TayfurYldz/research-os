"""SD-G5 HunterFamily registry + V3 hunt queue.

Revision ID: a29_001_hunter_family_registry
Revises: a28_001_token_economy
Create Date: 2026-08-19

Adds hunter_family (data-driven hypothesis family registry) and hunt_v3_queue
(pending active-experiment queue). Registry seed rows for 5 families.
"""

from datetime import datetime, timezone
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from research_os.data.postgres.tables import hunter_family

revision: str = "a29_001_hunter_family_registry"
down_revision: Union[str, Sequence[str], None] = "a28_001_token_economy"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SEED_FAMILIES = [
    {
        "family_id": "hf-object-authz",
        "name": "OBJECT_AUTHORIZATION",
        "target_node_kinds": ["HTTP_OPERATION", "RESOURCE_INSTANCE_CANDIDATE"],
        "preconditions": {"scope_classification": "IN_SCOPE"},
        "claim_template": (
            "Object authorization boundary on {origin}{path} "
            "may allow cross-owner access to {resource_id}."
        ),
        "evidence_requirements": {
            "required_observation_kinds": ["HTTP_AUTHORIZATION_DIFFERENTIAL"],
        },
        "validation_tier": "V3",
        "enabled": True,
        "version": 1,
    },
    {
        "family_id": "hf-workflow-trans",
        "name": "WORKFLOW_STATE_TRANSITION",
        "target_node_kinds": ["WORKFLOW_TRANSITION"],
        "preconditions": {"scope_classification": "IN_SCOPE"},
        "claim_template": (
            "Workflow transition {transition} on {resource_id} at {origin}{path} "
            "may lack authorization check."
        ),
        "evidence_requirements": {
            "required_observation_kinds": ["HTTP_STATE_TRANSITION_AUTHORIZATION"],
        },
        "validation_tier": "V3",
        "enabled": True,
        "version": 1,
    },
    {
        "family_id": "hf-exposed-api-spec",
        "name": "EXPOSED_API_SPEC",
        "target_node_kinds": ["API_SPEC"],
        "preconditions": {"scope_classification": "IN_SCOPE"},
        "claim_template": (
            "API specification at {canonical_key} documents endpoint surface "
            "that may be wider than observed access controls."
        ),
        "evidence_requirements": {
            "required_fact_kinds": ["API_SPEC"],
        },
        "validation_tier": "V2",
        "enabled": True,
        "version": 1,
    },
    {
        "family_id": "hf-unprotected-hostname",
        "name": "UNPROTECTED_HOSTNAME",
        "target_node_kinds": ["HOSTNAME"],
        "preconditions": {
            "scope_classification": "IN_SCOPE",
            "absent_edge_kind": "OBSERVED_UNDER",
        },
        "claim_template": (
            "Hostname {canonical_key} is in scope but has no observed "
            "active probe coverage yet."
        ),
        "evidence_requirements": {"required_edge_kind": "OBSERVED_UNDER"},
        "validation_tier": "V2",
        "enabled": True,
        "version": 1,
    },
    {
        "family_id": "hf-tech-cve-surface",
        "name": "TECH_KNOWN_CVE_SURFACE",
        "target_node_kinds": ["TECH"],
        "preconditions": {"scope_classification": "IN_SCOPE"},
        "claim_template": (
            "Technology {technology} at {canonical_key} is a candidate "
            "for known-vulnerability class verification."
        ),
        "evidence_requirements": {"required_fact_kinds": ["TECH"]},
        "validation_tier": "V2",
        "enabled": True,
        "version": 1,
    },
]


def upgrade() -> None:
    op.create_table(
        "hunter_family",
        sa.Column("family_id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "target_node_kinds",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "preconditions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("claim_template", sa.Text(), nullable=False),
        sa.Column(
            "evidence_requirements",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("validation_tier", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("family_id", "version"),
        sa.CheckConstraint(
            "validation_tier IN ('V1', 'V2', 'V3')",
            name="ck_hunter_family_validation_tier",
        ),
        sa.CheckConstraint("version >= 1", name="ck_hunter_family_version_positive"),
    )

    op.create_table(
        "hunt_v3_queue",
        sa.Column("queue_id", sa.Text(), nullable=False),
        sa.Column("research_run_id", sa.Text(), nullable=False),
        sa.Column("hypothesis_id", sa.Text(), nullable=False),
        sa.Column("family_id", sa.Text(), nullable=False),
        sa.Column("node_canonical_key", sa.Text(), nullable=False),
        sa.Column("capability", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column(
            "arguments",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("side_effect_level", sa.Integer(), nullable=False),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["research_run_id"],
            ["research_run.research_run_id"],
            name="fk_hunt_v3_queue_research_run",
        ),
        sa.ForeignKeyConstraint(
            ["hypothesis_id", "research_run_id"],
            ["hypothesis.hypothesis_id", "hypothesis.research_run_id"],
            name="fk_hunt_v3_queue_hypothesis_same_run",
        ),
        sa.PrimaryKeyConstraint("queue_id"),
        sa.CheckConstraint(
            "side_effect_level IN (0, 1, 2, 3)",
            name="ck_hunt_v3_queue_side_effect_level",
        ),
        sa.CheckConstraint(
            "state IN ('PENDING', 'APPROVED', 'RUN', 'BLOCKED')",
            name="ck_hunt_v3_queue_state",
        ),
    )

    op.bulk_insert(
        hunter_family,
        [
            {
                **family,
                "created_at": datetime.now(timezone.utc),
            }
            for family in SEED_FAMILIES
        ],
    )


def downgrade() -> None:
    op.drop_table("hunt_v3_queue")
    op.drop_table("hunter_family")
