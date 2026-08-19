"""SD-G2 discovery fact kind expansion.

Revision ID: a25_001_discovery_fact_kinds
Revises: a24_001_sensor_plane
Create Date: 2026-08-19

Expands the discovery_fact fact_kind check constraint to include the
sensor-derived external census kinds introduced by SD-G2.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "a25_001_discovery_fact_kinds"
down_revision: Union[str, Sequence[str], None] = "a24_001_sensor_plane"
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
    # SD-G2 sensor-derived external census kinds.
    "DOMAIN",
    "HOSTNAME",
    "CERT",
    "SERVICE",
    "TECH",
    "JS_BUNDLE",
    "API_SPEC",
)


def upgrade() -> None:
    op.drop_constraint("ck_discovery_fact_kind", "discovery_fact", type_="check")
    op.create_check_constraint(
        "ck_discovery_fact_kind",
        "discovery_fact",
        "fact_kind IN (" + ", ".join(f"'{item}'" for item in FACT_KINDS) + ")",
    )


def downgrade() -> None:
    op.drop_constraint("ck_discovery_fact_kind", "discovery_fact", type_="check")
    op.create_check_constraint(
        "ck_discovery_fact_kind",
        "discovery_fact",
        "fact_kind IN ('ORIGIN', 'EXACT_PATH', 'HTTP_OPERATION', 'PAGE_STATE', "
        "'CONTROL', 'FORM', 'RESPONSE_SHAPE', 'RESOURCE_INSTANCE_CANDIDATE', "
        "'WORKFLOW_STATE', 'WORKFLOW_TRANSITION', 'SCOPE_BOUNDARY_CANDIDATE')",
    )
