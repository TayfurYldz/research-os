"""Data-layer errors. Distinct from Core policy DENY and from CoreInputError."""


class PersistenceError(Exception):
    """Persistence adapter failure (integrity, connectivity, append-only violation)."""


class PersistenceConflictError(PersistenceError):
    """Unique/idempotency conflict. Not a policy decision and not duplicate Evidence."""


class PersistenceInputError(PersistenceError):
    """Invalid record passed to a repository. Not a policy decision."""


class BudgetOverspendError(PersistenceError):
    """Append would exceed IssuedBudget. Not a research conclusion."""
