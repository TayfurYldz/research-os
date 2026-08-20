"""Extend program platform constraint for public bug bounty platforms.

Revision ID: a34_001_program_platforms
Revises: a33_001_hypothesis_identity
Create Date: 2026-08-20
"""

from typing import Sequence, Union

from alembic import op

revision: str = "a34_001_program_platforms"
down_revision: Union[str, Sequence[str], None] = "a33_001_hypothesis_identity"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PREVIOUS_PLATFORMS = ("hackerone", "bugcrowd", "manual")
PLATFORMS = ("hackerone", "bugcrowd", "manual", "yeswehack", "intigriti", "other")


def _platform_constraint(platforms: tuple[str, ...]) -> str:
    values = ", ".join(repr(item) for item in platforms)
    return f"platform IS NULL OR platform IN ({values})"


def upgrade() -> None:
    op.drop_constraint("ck_program_platform", "program", type_="check")
    op.create_check_constraint(
        "ck_program_platform",
        "program",
        _platform_constraint(PLATFORMS),
    )


def downgrade() -> None:
    op.drop_constraint("ck_program_platform", "program", type_="check")
    op.create_check_constraint(
        "ck_program_platform",
        "program",
        _platform_constraint(PREVIOUS_PLATFORMS),
    )
