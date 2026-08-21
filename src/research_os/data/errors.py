"""Data-layer errors. Distinct from Core policy DENY and from CoreInputError."""


class PersistenceError(Exception):
    """Persistence adapter failure (integrity, connectivity, append-only violation)."""


class PersistenceConflictError(PersistenceError):
    """Unique/idempotency conflict. Not a policy decision and not duplicate Evidence."""


class PersistenceInputError(PersistenceError):
    """Invalid record passed to a repository. Not a policy decision."""


class BudgetOverspendError(PersistenceError):
    """Append would exceed IssuedBudget. Not a research conclusion."""


class TerminalOrchestrationStateError(PersistenceError):
    """Write rejected because the persisted research_orchestration row is terminal.

    Terminal orchestration states (COMPLETED, BUDGET_EXHAUSTED,
    FAILED_OPERATIONAL) are immutable once persisted. No operator command and
    no internal transition may overwrite state or stop_reason on a terminal
    row; this is enforced at the repository boundary so it holds regardless
    of which caller attempts the write.
    """
