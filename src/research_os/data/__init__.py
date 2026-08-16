"""Data: authoritative PostgreSQL persistence spine (Decision 020).

Python records/ports here are not language-neutral contracts.
SQLAlchemy/psycopg live only in `research_os.data.postgres`.
"""

from research_os.data.errors import PersistenceError, PersistenceInputError
from research_os.data.records import (
    AuditEventRecord,
    AuthorizationSourceRecord,
    ExperimentExecutionState,
    ExperimentRecord,
    HypothesisRecord,
    IssuedBudgetRecord,
    ObservationRecord,
    ProgramRecord,
    ResearchRunRecord,
    WorkerResultRecord,
    WorkerResultStatus,
)
from research_os.data.unit_of_work import UnitOfWork

__all__ = [
    "AuditEventRecord",
    "AuthorizationSourceRecord",
    "ExperimentExecutionState",
    "ExperimentRecord",
    "HypothesisRecord",
    "IssuedBudgetRecord",
    "ObservationRecord",
    "PersistenceError",
    "PersistenceInputError",
    "ProgramRecord",
    "ResearchRunRecord",
    "UnitOfWork",
    "WorkerResultRecord",
    "WorkerResultStatus",
]
