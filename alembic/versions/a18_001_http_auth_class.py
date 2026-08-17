"""Allow HTTP_AUTHORIZATION_DIFFERENTIAL classification on Candidate/Finding records.

Revision ID: a18_001_http_auth_class
Revises: a17_001_qa_remediation
Create Date: 2026-08-17

Does not rewrite a3–a17.
Classification is a bounded claim type, not CVSS and not a Finding until Human/Core Approval.
alembic_version.version_num is VARCHAR(32); keep revision ids within that bound.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "a18_001_http_auth_class"
down_revision: Union[str, Sequence[str], None] = "a17_001_qa_remediation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CLASSIFICATIONS = "IN ('DIAGNOSTIC_PLUMBING', 'HTTP_AUTHORIZATION_DIFFERENTIAL')"
_OLD = "IN ('DIAGNOSTIC_PLUMBING')"


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
