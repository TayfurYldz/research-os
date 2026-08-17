"""Allow HTTP_STATE_TRANSITION_AUTHORIZATION classification on Candidate/Finding records.

Revision ID: a19_001_http_state_class
Revises: a18_001_http_auth_class
Create Date: 2026-08-17

Required because candidate/finding CHECK constraints only allow the prior
classifications. GATE 16 introduces a second security class that must not be
stored as HTTP_AUTHORIZATION_DIFFERENTIAL. Does not rewrite a3–a18.
alembic_version.version_num is VARCHAR(32); keep revision ids within that bound.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "a19_001_http_state_class"
down_revision: Union[str, Sequence[str], None] = "a18_001_http_auth_class"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CLASSIFICATIONS = (
    "IN ('DIAGNOSTIC_PLUMBING', 'HTTP_AUTHORIZATION_DIFFERENTIAL', "
    "'HTTP_STATE_TRANSITION_AUTHORIZATION')"
)
_OLD = "IN ('DIAGNOSTIC_PLUMBING', 'HTTP_AUTHORIZATION_DIFFERENTIAL')"


def upgrade() -> None:
    op.drop_constraint("ck_candidate_classification", "candidate", type_="check")
    op.create_check_constraint(
        "ck_candidate_classification",
        "candidate",
        f"classification {_CLASSIFICATIONS}",
    )
    op.drop_constraint(
        "ck_candidate_admission_classification", "candidate_admission", type_="check"
    )
    op.create_check_constraint(
        "ck_candidate_admission_classification",
        "candidate_admission",
        f"classification IS NULL OR classification {_CLASSIFICATIONS}",
    )
    op.drop_constraint(
        "ck_finding_proposal_classification", "finding_proposal", type_="check"
    )
    op.create_check_constraint(
        "ck_finding_proposal_classification",
        "finding_proposal",
        f"classification {_CLASSIFICATIONS}",
    )
    op.drop_constraint("ck_finding_classification", "finding", type_="check")
    op.create_check_constraint(
        "ck_finding_classification",
        "finding",
        f"classification {_CLASSIFICATIONS}",
    )


def downgrade() -> None:
    op.drop_constraint("ck_finding_classification", "finding", type_="check")
    op.create_check_constraint(
        "ck_finding_classification",
        "finding",
        f"classification {_OLD}",
    )
    op.drop_constraint(
        "ck_finding_proposal_classification", "finding_proposal", type_="check"
    )
    op.create_check_constraint(
        "ck_finding_proposal_classification",
        "finding_proposal",
        f"classification {_OLD}",
    )
    op.drop_constraint(
        "ck_candidate_admission_classification", "candidate_admission", type_="check"
    )
    op.create_check_constraint(
        "ck_candidate_admission_classification",
        "candidate_admission",
        f"classification IS NULL OR classification {_OLD}",
    )
    op.drop_constraint("ck_candidate_classification", "candidate", type_="check")
    op.create_check_constraint(
        "ck_candidate_classification",
        "candidate",
        f"classification {_OLD}",
    )
