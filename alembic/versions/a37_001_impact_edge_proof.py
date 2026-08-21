"""Add proof_refs to impact_chain_edge (Slice 6 / epistemic hardening).

Additive column only. Nodes already require non-empty proof_refs; edges
asserting ENABLES/ESCALATES/CONFIRMS now carry independent proof of the
relation. Existing empty tables get an empty JSON array default that the
record layer rejects on read, so new writes must supply proofs.

Revision ID: a37_001_impact_edge_proof
Revises: a36_001_opportunity_candidate
Create Date: 2026-08-21
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a37_001_impact_edge_proof"
down_revision: Union[str, Sequence[str], None] = "a36_001_opportunity_candidate"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "impact_chain_edge",
        sa.Column(
            "proof_refs",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.alter_column("impact_chain_edge", "proof_refs", server_default=None)


def downgrade() -> None:
    op.drop_column("impact_chain_edge", "proof_refs")
