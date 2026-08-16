"""Research-facing experiment feedback. Not a vulnerability verdict."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from research_os.research.types import ResearchInputError


def _require_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ResearchInputError(f"{field_name} must be a non-empty string")
    return value


@dataclass(frozen=True)
class ExperimentFeedback:
    """Structured outcome references for later belief update. Not Evidence."""

    hypothesis_id: str
    experiment_id: str
    execution_outcome: str
    observation_ids: tuple[str, ...]
    research_run_id: str
    context_fingerprint: str | None = None
    notes: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "hypothesis_id", _require_text(self.hypothesis_id, "hypothesis_id")
        )
        object.__setattr__(
            self, "experiment_id", _require_text(self.experiment_id, "experiment_id")
        )
        object.__setattr__(
            self,
            "execution_outcome",
            _require_text(self.execution_outcome, "execution_outcome"),
        )
        object.__setattr__(
            self,
            "research_run_id",
            _require_text(self.research_run_id, "research_run_id"),
        )
        if not isinstance(self.observation_ids, tuple):
            raise ResearchInputError("observation_ids must be a tuple")
        if self.notes is not None and not isinstance(self.notes, Mapping):
            raise ResearchInputError("notes must be a mapping")
        if self.notes is not None:
            object.__setattr__(self, "notes", dict(self.notes))
