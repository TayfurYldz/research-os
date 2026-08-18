"""GATE 01 scope compiler v2 + ProgramResearchContext.

Revision ID: a23_001_program_scope
Revises: a22_001_discovery_surface
Create Date: 2026-08-19

Program policy is Core data, not prompt. Scope rules v2 support wildcard patterns
and explicit expiration. Rate limits derive from Core budget. Bounty tables are
program-level reference data.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a23_001_program_scope"
down_revision: Union[str, Sequence[str], None] = "a22_001_discovery_surface"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCOPE_RULE_EFFECTS = ("ALLOW", "DENY", "OUT_OF_SCOPE", "UNKNOWN")
PLATFORMS = ("hackerone", "bugcrowd", "manual")
SEVERITIES = ("P1", "P2", "P3", "P4", "P5")


def upgrade() -> None:
    # Program already exists (a3_001_persistence_spine). Enrich it for sync.
    op.add_column("program", sa.Column("handle", sa.Text(), nullable=True))
    op.add_column("program", sa.Column("platform", sa.Text(), nullable=True))
    op.create_check_constraint(
        "ck_program_platform",
        "program",
        f"platform IS NULL OR platform IN ({', '.join(repr(item) for item in PLATFORMS)})",
    )

    op.create_table(
        "scope_rule_v2",
        sa.Column("rule_id", sa.Text(), nullable=False),
        sa.Column("program_id", sa.Text(), nullable=False),
        sa.Column("effect", sa.Text(), nullable=False),
        sa.Column("scheme", sa.Text(), nullable=False),
        sa.Column("host", sa.Text(), nullable=True),
        sa.Column("host_pattern", sa.Text(), nullable=True),
        sa.Column("port", sa.Integer(), nullable=True),
        sa.Column("path_prefix", sa.Text(), nullable=True),
        sa.Column("source_reference", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["program_id"], ["program.program_id"]),
        sa.PrimaryKeyConstraint("rule_id"),
        sa.UniqueConstraint("rule_id", "program_id", name="uq_scope_rule_v2_id_program"),
        sa.CheckConstraint(
            f"effect IN ({', '.join(repr(item) for item in SCOPE_RULE_EFFECTS)})",
            name="ck_scope_rule_v2_effect",
        ),
        sa.CheckConstraint(
            "scheme IN ('http', 'https')",
            name="ck_scope_rule_v2_scheme",
        ),
        sa.CheckConstraint(
            "(host IS NOT NULL AND host_pattern IS NULL) OR "
            "(host IS NULL AND host_pattern IS NOT NULL)",
            name="ck_scope_rule_v2_host_xor_pattern",
        ),
        sa.CheckConstraint(
            "host_pattern IS NULL OR host_pattern LIKE '*.%'",
            name="ck_scope_rule_v2_host_pattern_format",
        ),
        sa.CheckConstraint(
            "port IS NULL OR port >= 1",
            name="ck_scope_rule_v2_port_positive",
        ),
        sa.CheckConstraint(
            "path_prefix IS NULL OR path_prefix LIKE '/%'",
            name="ck_scope_rule_v2_path_prefix_absolute",
        ),
        sa.CheckConstraint(
            "expires_at IS NULL OR created_at <= expires_at",
            name="ck_scope_rule_v2_expires_after_created",
        ),
    )

    op.create_table(
        "program_policy",
        sa.Column("program_id", sa.Text(), nullable=False),
        sa.Column("loopback_fixture", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("max_response_bytes", sa.Integer(), nullable=False, server_default="4096"),
        sa.Column("timeout_ms", sa.Integer(), nullable=False, server_default="2000"),
        sa.Column("action_policy", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["program_id"], ["program.program_id"]),
        sa.PrimaryKeyConstraint("program_id"),
        sa.CheckConstraint(
            "max_response_bytes >= 0",
            name="ck_program_policy_max_response_bytes",
        ),
        sa.CheckConstraint(
            "timeout_ms >= 0",
            name="ck_program_policy_timeout_ms",
        ),
    )

    op.create_table(
        "rate_limit_profile",
        sa.Column("profile_id", sa.Text(), nullable=False),
        sa.Column("program_id", sa.Text(), nullable=False),
        sa.Column("max_requests_per_window", sa.Integer(), nullable=False),
        sa.Column("window_seconds", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["program_id"], ["program.program_id"]),
        sa.PrimaryKeyConstraint("profile_id"),
        sa.UniqueConstraint("program_id", name="uq_rate_limit_profile_program"),
        sa.CheckConstraint(
            "max_requests_per_window >= 0",
            name="ck_rate_limit_max_requests",
        ),
        sa.CheckConstraint(
            "window_seconds >= 0",
            name="ck_rate_limit_window_seconds",
        ),
    )

    op.create_table(
        "bounty_table",
        sa.Column("program_id", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("reward_range", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["program_id"], ["program.program_id"]),
        sa.PrimaryKeyConstraint("program_id", "severity"),
        sa.CheckConstraint(
            f"severity IN ({', '.join(repr(item) for item in SEVERITIES)})",
            name="ck_bounty_table_severity",
        ),
    )


def downgrade() -> None:
    op.drop_table("bounty_table")
    op.drop_table("rate_limit_profile")
    op.drop_table("program_policy")
    op.drop_table("scope_rule_v2")
    op.drop_constraint("ck_program_platform", "program", type_="check")
    op.drop_column("program", "platform")
    op.drop_column("program", "handle")
