"""SD-G7 ImpactGraph tables.

Revision ID: a31_001_impact_graph
Revises: a30_001_oast_token
Create Date: 2026-08-19

Adds impact_chain, impact_chain_node, impact_chain_edge tables and the
impact_chain_ids column on finding_proposal.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a31_001_impact_graph"
down_revision: Union[str, Sequence[str], None] = "a30_001_oast_token"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "impact_chain",
        sa.Column("chain_id", sa.Text(), nullable=False),
        sa.Column("research_run_id", sa.Text(), nullable=False),
        sa.Column("program_id", sa.Text(), nullable=False),
        sa.Column("graph_hash", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["research_run_id"],
            ["research_run.research_run_id"],
            name="fk_impact_chain_research_run",
        ),
        sa.ForeignKeyConstraint(
            ["program_id"],
            ["program.program_id"],
            name="fk_impact_chain_program",
        ),
        sa.PrimaryKeyConstraint("chain_id", name="pk_impact_chain"),
        sa.UniqueConstraint(
            "chain_id", "research_run_id", name="uq_impact_chain_id_run"
        ),
        sa.CheckConstraint(
            "graph_hash IS NULL OR length(graph_hash) = 64",
            name="ck_impact_chain_graph_hash_length",
        ),
    )
    op.create_table(
        "impact_chain_node",
        sa.Column("node_id", sa.Text(), nullable=False),
        sa.Column("chain_id", sa.Text(), nullable=False),
        sa.Column("impact_kind", sa.Text(), nullable=False),
        sa.Column("claim_text", sa.Text(), nullable=False),
        sa.Column("scope_ref", postgresql.JSONB(), nullable=False),
        sa.Column("proof_refs", postgresql.JSONB(), nullable=False),
        sa.Column("ordering", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["chain_id"],
            ["impact_chain.chain_id"],
            name="fk_impact_chain_node_chain",
        ),
        sa.PrimaryKeyConstraint("node_id", name="pk_impact_chain_node"),
        sa.CheckConstraint("ordering >= 0", name="ck_impact_chain_node_ordering"),
    )
    op.create_table(
        "impact_chain_edge",
        sa.Column("edge_id", sa.Text(), nullable=False),
        sa.Column("chain_id", sa.Text(), nullable=False),
        sa.Column("from_node_id", sa.Text(), nullable=False),
        sa.Column("to_node_id", sa.Text(), nullable=False),
        sa.Column("relation", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["chain_id"],
            ["impact_chain.chain_id"],
            name="fk_impact_chain_edge_chain",
        ),
        sa.PrimaryKeyConstraint("edge_id", name="pk_impact_chain_edge"),
        sa.CheckConstraint(
            "relation IN ('ENABLES', 'ESCALATES', 'CONFIRMS')",
            name="ck_impact_chain_edge_relation",
        ),
    )
    op.add_column(
        "finding_proposal",
        sa.Column(
            "impact_chain_ids",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("finding_proposal", "impact_chain_ids")
    op.drop_table("impact_chain_edge")
    op.drop_table("impact_chain_node")
    op.drop_table("impact_chain")
