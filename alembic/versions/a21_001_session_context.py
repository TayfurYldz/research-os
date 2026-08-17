"""Durable session metadata without cookie/token values.

Revision ID: a21_001_session_context
Revises: a20_001_capability_plan_binding
Create Date: 2026-08-17

Restart proof: metadata may remain ACTIVE, but session cookie/token values are
not stored here. If SecretPort cannot resolve SESSION_MATERIAL after restart,
execution fail-closes and requires reauthentication. Never fabricate a session
from metadata alone.
alembic_version.version_num is VARCHAR(32); keep revision ids within that bound.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a21_001_session_context"
down_revision: Union[str, Sequence[str], None] = "a20_001_capability_plan_binding"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "session_context",
        sa.Column("session_context_id", sa.Text(), nullable=False),
        sa.Column("research_run_id", sa.Text(), nullable=False),
        sa.Column("identity_id", sa.Text(), nullable=False),
        sa.Column("actor_reference", sa.Text(), nullable=False),
        sa.Column("origin", sa.Text(), nullable=False),
        sa.Column("authentication_profile_reference", sa.Text(), nullable=False),
        sa.Column("authentication_method", sa.Text(), nullable=False),
        sa.Column("secret_scheme", sa.Text(), nullable=False),
        sa.Column("secret_name", sa.Text(), nullable=False),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("established_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("session_cookie_name", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["research_run_id"], ["research_run.research_run_id"]),
        sa.PrimaryKeyConstraint("session_context_id"),
        sa.UniqueConstraint("session_context_id", "research_run_id", name="uq_session_context_id_run"),
        sa.CheckConstraint(
            "state IN ('NEW', 'AUTHENTICATING', 'ACTIVE', 'EXPIRED', 'REVOKED', 'FAILED')",
            name="ck_session_context_state",
        ),
        sa.CheckConstraint(
            "authentication_method IN ('HTTP_FORM_LOGIN')",
            name="ck_session_context_auth_method",
        ),
    )


def downgrade() -> None:
    op.drop_table("session_context")
