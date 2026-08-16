"""Persistence records for the A3 authoritative spine.

These are Data-layer Python types, not language-neutral contracts and not Core
authorization objects. Hypothesis is not fact, Evidence, or Finding.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Mapping

from research_os.core.enums import ActorType, AuthorizationSourceState
from research_os.data.errors import PersistenceInputError

SECRET_VALUE_KEYS = {
    "token",
    "password",
    "api_key",
    "apiKey",
    "raw_secret",
    "credential",
    "secret_value",
    "secretValue",
}

ALLOWED_ACTOR_TYPES = frozenset(item.value for item in ActorType)
ALLOWED_AUTHORIZATION_STATES = frozenset(
    item.value for item in AuthorizationSourceState
)


class ExperimentExecutionState(Enum):
    """Experiment execution outcome. Not Hypothesis belief. Not a Finding."""

    PLANNED = "PLANNED"
    AUTHORIZATION_CHECK = "AUTHORIZATION_CHECK"
    READY = "READY"
    RUNNING = "RUNNING"
    EXECUTION_SUCCEEDED = "EXECUTION_SUCCEEDED"
    EXECUTION_FAILED = "EXECUTION_FAILED"
    BLOCKED = "BLOCKED"
    CANCELLED = "CANCELLED"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"


class WorkerResultStatus(Enum):
    """Untrusted execution status from the Worker contract. Not Evidence."""

    SUCCEEDED = "SUCCEEDED"
    EXECUTION_FAILED = "EXECUTION_FAILED"
    BLOCKED = "BLOCKED"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    REAUTHORIZATION_REQUIRED = "REAUTHORIZATION_REQUIRED"


ALLOWED_EXPERIMENT_STATES = frozenset(
    item.value for item in ExperimentExecutionState
)
ALLOWED_WORKER_RESULT_STATUSES = frozenset(item.value for item in WorkerResultStatus)


def require_opaque_id(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PersistenceInputError(f"{field_name} must be a non-empty opaque id")
    return value


def require_aware_datetime(value: datetime, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise PersistenceInputError(f"{field_name} must be datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise PersistenceInputError(f"{field_name} must be timezone-aware")
    return value


def require_non_negative_int(value: int, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise PersistenceInputError(
            f"{field_name} must be a non-negative int; 0 is not unlimited"
        )
    return value


def _reject_secret_keys(payload: Mapping[str, Any] | None, field_name: str) -> None:
    if payload is None:
        return
    if not isinstance(payload, Mapping):
        raise PersistenceInputError(f"{field_name} must be a mapping")
    found = SECRET_VALUE_KEYS.intersection(payload.keys())
    if found:
        raise PersistenceInputError(
            f"{field_name} must not contain secret-value keys: {sorted(found)}"
        )


def _optional_mapping(
    value: Mapping[str, Any] | None, field_name: str
) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise PersistenceInputError(f"{field_name} must be a mapping")
    _reject_secret_keys(value, field_name)
    return dict(value)


@dataclass(frozen=True)
class ProgramRecord:
    program_id: str
    created_at: datetime
    name: str | None = None

    def __post_init__(self) -> None:
        require_opaque_id(self.program_id, "program_id")
        require_aware_datetime(self.created_at, "created_at")
        if self.name is not None and not isinstance(self.name, str):
            raise PersistenceInputError("name must be a string or None")


@dataclass(frozen=True)
class AuthorizationSourceRecord:
    authorization_source_id: str
    program_id: str
    state: str
    provenance_reference: str
    created_at: datetime
    effective_from: datetime | None = None
    effective_until: datetime | None = None

    def __post_init__(self) -> None:
        require_opaque_id(self.authorization_source_id, "authorization_source_id")
        require_opaque_id(self.program_id, "program_id")
        require_opaque_id(self.provenance_reference, "provenance_reference")
        require_aware_datetime(self.created_at, "created_at")
        if self.state not in ALLOWED_AUTHORIZATION_STATES:
            raise PersistenceInputError("state must be ACTIVE, EXPIRED, or REVOKED")
        if self.effective_from is not None:
            require_aware_datetime(self.effective_from, "effective_from")
        if self.effective_until is not None:
            require_aware_datetime(self.effective_until, "effective_until")
        if (
            self.effective_from is not None
            and self.effective_until is not None
            and self.effective_until < self.effective_from
        ):
            raise PersistenceInputError(
                "effective_until must be >= effective_from when both are set"
            )


@dataclass(frozen=True)
class ResearchRunRecord:
    research_run_id: str
    program_id: str
    authorization_source_id: str
    initiated_by_actor_id: str
    initiated_by_actor_type: str
    started_at: datetime

    def __post_init__(self) -> None:
        require_opaque_id(self.research_run_id, "research_run_id")
        require_opaque_id(self.program_id, "program_id")
        require_opaque_id(self.authorization_source_id, "authorization_source_id")
        require_opaque_id(self.initiated_by_actor_id, "initiated_by_actor_id")
        require_aware_datetime(self.started_at, "started_at")
        if self.initiated_by_actor_type not in ALLOWED_ACTOR_TYPES:
            raise PersistenceInputError(
                "initiated_by_actor_type must be a locked identity class; MODEL is not an actor"
            )


@dataclass(frozen=True)
class IssuedBudgetRecord:
    """Immutable Core-issued envelope. 0 is no allowance, never unlimited."""

    budget_id: str
    research_run_id: str
    max_requests: int
    max_tool_calls: int
    max_runtime_ms: int
    max_concurrency: int
    issued_at: datetime

    def __post_init__(self) -> None:
        require_opaque_id(self.budget_id, "budget_id")
        require_opaque_id(self.research_run_id, "research_run_id")
        require_non_negative_int(self.max_requests, "max_requests")
        require_non_negative_int(self.max_tool_calls, "max_tool_calls")
        require_non_negative_int(self.max_runtime_ms, "max_runtime_ms")
        require_non_negative_int(self.max_concurrency, "max_concurrency")
        require_aware_datetime(self.issued_at, "issued_at")


@dataclass(frozen=True)
class HypothesisRecord:
    """A claim to test. Not fact, Evidence, Candidate, or Finding."""

    hypothesis_id: str
    research_run_id: str
    claim: str
    created_at: datetime
    origin_reference: str | None = None

    def __post_init__(self) -> None:
        require_opaque_id(self.hypothesis_id, "hypothesis_id")
        require_opaque_id(self.research_run_id, "research_run_id")
        require_aware_datetime(self.created_at, "created_at")
        if not isinstance(self.claim, str) or not self.claim.strip():
            raise PersistenceInputError("claim must be a non-empty string")
        if self.origin_reference is not None:
            require_opaque_id(self.origin_reference, "origin_reference")


@dataclass(frozen=True)
class ExperimentRecord:
    experiment_id: str
    research_run_id: str
    hypothesis_id: str
    budget_id: str
    execution_state: str
    created_at: datetime

    def __post_init__(self) -> None:
        require_opaque_id(self.experiment_id, "experiment_id")
        require_opaque_id(self.research_run_id, "research_run_id")
        require_opaque_id(self.hypothesis_id, "hypothesis_id")
        require_opaque_id(self.budget_id, "budget_id")
        require_aware_datetime(self.created_at, "created_at")
        if self.execution_state not in ALLOWED_EXPERIMENT_STATES:
            raise PersistenceInputError("execution_state is not a domain execution state")


@dataclass(frozen=True)
class WorkerResultRecord:
    """UNTRUSTED EXECUTION OUTPUT. Insert does not create Observation or Evidence."""

    worker_result_id: str
    experiment_id: str
    research_run_id: str
    request_id: str
    correlation_id: str
    worker_capability: str
    action: str
    authorization_decision_reference: str
    budget_id: str
    side_effect_level: int
    contract_version: str
    worker_id: str
    status: str
    received_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    parent_request_id: str | None = None
    raw_result: Mapping[str, Any] | None = None
    raw_artifact_descriptors: list[Mapping[str, Any]] | None = None
    diagnostics: Mapping[str, Any] | None = None
    control_signal: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        require_opaque_id(self.worker_result_id, "worker_result_id")
        require_opaque_id(self.experiment_id, "experiment_id")
        require_opaque_id(self.research_run_id, "research_run_id")
        require_opaque_id(self.request_id, "request_id")
        require_opaque_id(self.correlation_id, "correlation_id")
        require_opaque_id(self.worker_capability, "worker_capability")
        require_opaque_id(self.action, "action")
        require_opaque_id(
            self.authorization_decision_reference, "authorization_decision_reference"
        )
        require_opaque_id(self.budget_id, "budget_id")
        require_opaque_id(self.worker_id, "worker_id")
        require_aware_datetime(self.received_at, "received_at")
        if not isinstance(self.contract_version, str) or not self.contract_version.strip():
            raise PersistenceInputError("contract_version must be a non-empty string")
        if self.status not in ALLOWED_WORKER_RESULT_STATUSES:
            raise PersistenceInputError("status is not a WorkerResult execution status")
        if self.side_effect_level not in (0, 1, 2, 3):
            raise PersistenceInputError("side_effect_level must be 0, 1, 2, or 3")
        if self.started_at is not None:
            require_aware_datetime(self.started_at, "started_at")
        if self.completed_at is not None:
            require_aware_datetime(self.completed_at, "completed_at")
        if self.parent_request_id is not None:
            require_opaque_id(self.parent_request_id, "parent_request_id")
        object.__setattr__(
            self, "raw_result", _optional_mapping(self.raw_result, "raw_result")
        )
        object.__setattr__(
            self, "diagnostics", _optional_mapping(self.diagnostics, "diagnostics")
        )
        object.__setattr__(
            self,
            "control_signal",
            _optional_mapping(self.control_signal, "control_signal"),
        )
        if self.raw_artifact_descriptors is not None:
            if not isinstance(self.raw_artifact_descriptors, list):
                raise PersistenceInputError("raw_artifact_descriptors must be a list")
            cleaned: list[Mapping[str, Any]] = []
            for index, item in enumerate(self.raw_artifact_descriptors):
                mapped = _optional_mapping(item, f"raw_artifact_descriptors[{index}]")
                if mapped is None:
                    raise PersistenceInputError("raw_artifact_descriptors items must be mappings")
                cleaned.append(mapped)
            object.__setattr__(self, "raw_artifact_descriptors", cleaned)


@dataclass(frozen=True)
class ObservationRecord:
    """Deterministic observed fact. Not a vulnerability and not Evidence."""

    observation_id: str
    worker_result_id: str
    observation_kind: str
    payload: Mapping[str, Any]
    normalization_version: str
    observed_at: datetime
    created_at: datetime

    def __post_init__(self) -> None:
        require_opaque_id(self.observation_id, "observation_id")
        require_opaque_id(self.worker_result_id, "worker_result_id")
        require_aware_datetime(self.observed_at, "observed_at")
        require_aware_datetime(self.created_at, "created_at")
        if not isinstance(self.observation_kind, str) or not self.observation_kind.strip():
            raise PersistenceInputError("observation_kind must be a non-empty string")
        if not isinstance(self.normalization_version, str) or not self.normalization_version.strip():
            raise PersistenceInputError("normalization_version must be a non-empty string")
        if not isinstance(self.payload, Mapping):
            raise PersistenceInputError("payload must be a mapping")
        _reject_secret_keys(self.payload, "payload")
        object.__setattr__(self, "payload", dict(self.payload))


@dataclass(frozen=True)
class AuditEventRecord:
    """Append-only reconstructive history. Not Evidence. Not a log substitute."""

    audit_event_id: str
    occurred_at: datetime
    actor_id: str
    actor_type: str
    event_type: str
    subject_type: str
    subject_id: str
    payload: Mapping[str, Any]
    correlation_id: str | None = None

    def __post_init__(self) -> None:
        require_opaque_id(self.audit_event_id, "audit_event_id")
        require_opaque_id(self.actor_id, "actor_id")
        require_opaque_id(self.subject_id, "subject_id")
        require_aware_datetime(self.occurred_at, "occurred_at")
        if self.actor_type not in ALLOWED_ACTOR_TYPES:
            raise PersistenceInputError("actor_type must be a locked identity class")
        if not isinstance(self.event_type, str) or not self.event_type.strip():
            raise PersistenceInputError("event_type must be a non-empty string")
        if not isinstance(self.subject_type, str) or not self.subject_type.strip():
            raise PersistenceInputError("subject_type must be a non-empty string")
        if not isinstance(self.payload, Mapping):
            raise PersistenceInputError("payload must be a mapping")
        _reject_secret_keys(self.payload, "payload")
        object.__setattr__(self, "payload", dict(self.payload))
        if self.correlation_id is not None:
            require_opaque_id(self.correlation_id, "correlation_id")
