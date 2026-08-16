"""Data-layer errors. Distinct from Core policy DENY and from CoreInputError."""


class PersistenceError(Exception):
    """Persistence adapter failure (integrity, connectivity, append-only violation)."""


class PersistenceInputError(PersistenceError):
    """Invalid record passed to a repository. Not a policy decision."""
