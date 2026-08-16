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


class ExecutionAttemptState(Enum):
    """One intended Worker invocation. Not Evidence. Not Hypothesis outcome."""

    AUTHORIZED = "AUTHORIZED"
    DISPATCHING = "DISPATCHING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"
    CANCELLED = "CANCELLED"
    UNKNOWN_OUTCOME = "UNKNOWN_OUTCOME"


ALLOWED_EXECUTION_ATTEMPT_STATES = frozenset(
    item.value for item in ExecutionAttemptState
)

ALLOWED_REASONING_ROLES = frozenset({"GENERATOR", "FALSIFIER"})
ALLOWED_ADMISSION_OUTCOMES = frozenset(
    {
        "ADMITTED",
        "REJECTED_UNTESTABLE",
        "REJECTED_UNSUPPORTED",
        "REJECTED_POLICY_CONFLICT",
        "NEEDS_MORE_CONTEXT",
        "MODEL_INVOCATION_FAILED",
    }
)
ALLOWED_ASSESSMENT_OUTCOMES = frozenset(
    {
        "CONSISTENT_WITH_PREDICTION",
        "CONTRADICTS_PREDICTION",
        "INCONCLUSIVE",
        "EXECUTION_UNUSABLE",
        "NEEDS_MORE_CONTEXT",
    }
)
ALLOWED_EVALUATOR_KINDS = frozenset({"DETERMINISTIC"})
ASSESSMENT_RATIONALE_FORBIDDEN_KEYS = frozenset(
    {"severity", "evidence", "finding", "confidence", "candidate"}
)
ALLOWED_EVIDENCE_POLARITIES = frozenset({"SUPPORTING", "CONTRADICTING", "NEUTRAL"})
ALLOWED_EVIDENCE_ADMISSION_OUTCOMES = frozenset(
    {
        "ADMITTED",
        "REJECTED_INSUFFICIENT_SUPPORT",
        "REJECTED_BROKEN_PROVENANCE",
        "REJECTED_EXECUTION_UNUSABLE",
        "REJECTED_POLICY_CONFLICT",
        "NEEDS_VERIFICATION",
    }
)
EVIDENCE_FORBIDDEN_KEYS = frozenset(
    {
        "severity",
        "finding",
        "candidate",
        "exploitability",
        "authorization",
        "confidence",
        "verification",
    }
)


def require_opaque_id(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PersistenceInputError(f"{field_name} must be a non-empty opaque id")
    return value


def require_optional_opaque_id(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    return require_opaque_id(value, field_name)


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
class ResearchReasoningRecord:
    """Append-only untrusted reasoning provenance. Not Observation, Evidence, or Hypothesis truth."""

    reasoning_record_id: str
    research_run_id: str
    hypothesis_id: str | None
    role: str
    adapter_identity: str
    provider_adapter_identity: str
    correlation_id: str
    context_fingerprint: str
    structured_output: Mapping[str, Any]
    created_at: datetime
    model_id: str | None = None
    model_version: str | None = None

    def __post_init__(self) -> None:
        require_opaque_id(self.reasoning_record_id, "reasoning_record_id")
        require_opaque_id(self.research_run_id, "research_run_id")
        require_optional_opaque_id(self.hypothesis_id, "hypothesis_id")
        require_opaque_id(self.adapter_identity, "adapter_identity")
        require_opaque_id(self.provider_adapter_identity, "provider_adapter_identity")
        require_opaque_id(self.correlation_id, "correlation_id")
        require_aware_datetime(self.created_at, "created_at")
        if self.role not in ALLOWED_REASONING_ROLES:
            raise PersistenceInputError("role is not a Research reasoning role")
        if not isinstance(self.context_fingerprint, str) or not self.context_fingerprint.strip():
            raise PersistenceInputError("context_fingerprint must be a non-empty string")
        if not isinstance(self.structured_output, Mapping):
            raise PersistenceInputError("structured_output must be a mapping")
        _reject_secret_keys(self.structured_output, "structured_output")
        object.__setattr__(self, "structured_output", dict(self.structured_output))
        if self.model_id is not None:
            require_opaque_id(self.model_id, "model_id")
        if self.model_version is not None:
            if not isinstance(self.model_version, str) or not self.model_version.strip():
                raise PersistenceInputError("model_version must be a non-empty string when set")


@dataclass(frozen=True)
class ResearchAdmissionRecord:
    """Append-only research-process admission history. Not Hypothesis truth or Evidence."""

    admission_record_id: str
    research_run_id: str
    outcome: str
    reason: str
    reason_code: str
    context_fingerprint: str
    created_at: datetime
    generator_reasoning_record_id: str | None = None
    falsifier_reasoning_record_id: str | None = None
    admitted_hypothesis_id: str | None = None

    def __post_init__(self) -> None:
        require_opaque_id(self.admission_record_id, "admission_record_id")
        require_opaque_id(self.research_run_id, "research_run_id")
        require_aware_datetime(self.created_at, "created_at")
        if self.outcome not in ALLOWED_ADMISSION_OUTCOMES:
            raise PersistenceInputError("outcome is not a Research admission outcome")
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise PersistenceInputError("reason must be a non-empty string")
        if not isinstance(self.reason_code, str) or not self.reason_code.strip():
            raise PersistenceInputError("reason_code must be a non-empty string")
        if not isinstance(self.context_fingerprint, str) or not self.context_fingerprint.strip():
            raise PersistenceInputError("context_fingerprint must be a non-empty string")
        require_optional_opaque_id(
            self.generator_reasoning_record_id, "generator_reasoning_record_id"
        )
        require_optional_opaque_id(
            self.falsifier_reasoning_record_id, "falsifier_reasoning_record_id"
        )
        require_optional_opaque_id(self.admitted_hypothesis_id, "admitted_hypothesis_id")
        if self.outcome == "ADMITTED" and self.admitted_hypothesis_id is None:
            raise PersistenceInputError("ADMITTED admission requires admitted_hypothesis_id")
        if self.outcome != "ADMITTED" and self.admitted_hypothesis_id is not None:
            raise PersistenceInputError("rejected admission must not carry admitted_hypothesis_id")


@dataclass(frozen=True)
class ExperimentPlanRecord:
    """Immutable executed-plan specification. Not Experiment lifecycle and not authorization."""

    experiment_id: str
    research_run_id: str
    hypothesis_id: str
    required_capability: str
    action: str
    target_reference: str
    side_effect_level: int
    arguments: Mapping[str, Any]
    requested_budget_id: str
    expected_observation: str
    disconfirming_observation: str
    evaluation_strategy: str
    created_at: datetime

    def __post_init__(self) -> None:
        require_opaque_id(self.experiment_id, "experiment_id")
        require_opaque_id(self.research_run_id, "research_run_id")
        require_opaque_id(self.hypothesis_id, "hypothesis_id")
        require_opaque_id(self.required_capability, "required_capability")
        require_opaque_id(self.action, "action")
        require_opaque_id(self.target_reference, "target_reference")
        require_opaque_id(self.requested_budget_id, "requested_budget_id")
        require_aware_datetime(self.created_at, "created_at")
        if self.side_effect_level not in (0, 1, 2, 3):
            raise PersistenceInputError("side_effect_level must be 0, 1, 2, or 3")
        if not isinstance(self.expected_observation, str) or not self.expected_observation.strip():
            raise PersistenceInputError("expected_observation must be a non-empty string")
        if (
            not isinstance(self.disconfirming_observation, str)
            or not self.disconfirming_observation.strip()
        ):
            raise PersistenceInputError("disconfirming_observation must be a non-empty string")
        if not isinstance(self.evaluation_strategy, str) or not self.evaluation_strategy.strip():
            raise PersistenceInputError("evaluation_strategy must be a non-empty string")
        if not isinstance(self.arguments, Mapping):
            raise PersistenceInputError("arguments must be a mapping")
        _reject_secret_keys(self.arguments, "arguments")
        object.__setattr__(self, "arguments", dict(self.arguments))


@dataclass(frozen=True)
class HypothesisAssessmentRecord:
    """Append-only context-bound assessment. Not Evidence, Candidate, or Finding."""

    assessment_id: str
    hypothesis_id: str
    experiment_id: str
    research_run_id: str
    assessment_outcome: str
    observation_ids: tuple[str, ...]
    evaluator_kind: str
    evaluator_version: str
    rationale: Mapping[str, Any]
    evaluation_strategy: str
    created_at: datetime

    def __post_init__(self) -> None:
        require_opaque_id(self.assessment_id, "assessment_id")
        require_opaque_id(self.hypothesis_id, "hypothesis_id")
        require_opaque_id(self.experiment_id, "experiment_id")
        require_opaque_id(self.research_run_id, "research_run_id")
        require_aware_datetime(self.created_at, "created_at")
        if self.assessment_outcome not in ALLOWED_ASSESSMENT_OUTCOMES:
            raise PersistenceInputError("assessment_outcome is not a HypothesisAssessment outcome")
        if self.evaluator_kind not in ALLOWED_EVALUATOR_KINDS:
            raise PersistenceInputError("evaluator_kind is not a supported evaluator kind")
        if not isinstance(self.evaluator_version, str) or not self.evaluator_version.strip():
            raise PersistenceInputError("evaluator_version must be a non-empty string")
        if not isinstance(self.evaluation_strategy, str) or not self.evaluation_strategy.strip():
            raise PersistenceInputError("evaluation_strategy must be a non-empty string")
        if not isinstance(self.observation_ids, tuple):
            raise PersistenceInputError("observation_ids must be a tuple")
        cleaned_ids: list[str] = []
        for index, item in enumerate(self.observation_ids):
            cleaned_ids.append(require_opaque_id(item, f"observation_ids[{index}]"))
        object.__setattr__(self, "observation_ids", tuple(cleaned_ids))
        if not isinstance(self.rationale, Mapping):
            raise PersistenceInputError("rationale must be a mapping")
        found = ASSESSMENT_RATIONALE_FORBIDDEN_KEYS.intersection(self.rationale.keys())
        if found:
            raise PersistenceInputError(
                f"assessment rationale must not contain {sorted(found)}"
            )
        _reject_secret_keys(self.rationale, "rationale")
        object.__setattr__(self, "rationale", dict(self.rationale))


@dataclass(frozen=True)
class EvidenceRecord:
    """Append-only admitted Evidence. Not Candidate, Finding, or Verification."""

    evidence_id: str
    research_run_id: str
    hypothesis_id: str
    experiment_id: str
    admission_record_id: str
    polarity: str
    claim_scope: str
    observation_ids: tuple[str, ...]
    assessment_ids: tuple[str, ...]
    created_at: datetime

    def __post_init__(self) -> None:
        require_opaque_id(self.evidence_id, "evidence_id")
        require_opaque_id(self.research_run_id, "research_run_id")
        require_opaque_id(self.hypothesis_id, "hypothesis_id")
        require_opaque_id(self.experiment_id, "experiment_id")
        require_opaque_id(self.admission_record_id, "admission_record_id")
        require_aware_datetime(self.created_at, "created_at")
        if self.polarity not in ALLOWED_EVIDENCE_POLARITIES:
            raise PersistenceInputError("polarity is not an Evidence polarity")
        if not isinstance(self.claim_scope, str) or not self.claim_scope.strip():
            raise PersistenceInputError("claim_scope must be a non-empty string")
        if not isinstance(self.observation_ids, tuple) or not self.observation_ids:
            raise PersistenceInputError("observation_ids must be a non-empty tuple")
        cleaned: list[str] = []
        for index, item in enumerate(self.observation_ids):
            cleaned.append(require_opaque_id(item, f"observation_ids[{index}]"))
        object.__setattr__(self, "observation_ids", tuple(cleaned))
        if not isinstance(self.assessment_ids, tuple) or not self.assessment_ids:
            raise PersistenceInputError("assessment_ids must be a non-empty tuple")
        assessments: list[str] = []
        for index, item in enumerate(self.assessment_ids):
            assessments.append(require_opaque_id(item, f"assessment_ids[{index}]"))
        object.__setattr__(self, "assessment_ids", tuple(assessments))


@dataclass(frozen=True)
class EvidenceAdmissionRecord:
    """Append-only Evidence admission history. Rejected proposals create no Evidence."""

    admission_record_id: str
    proposal_id: str
    research_run_id: str
    outcome: str
    reason_codes: tuple[str, ...]
    observation_ids: tuple[str, ...]
    assessment_ids: tuple[str, ...]
    admission_policy_version: str
    evaluator_version: str
    created_at: datetime
    admitted_evidence_id: str | None = None
    claim_scope: str | None = None
    polarity: str | None = None

    def __post_init__(self) -> None:
        require_opaque_id(self.admission_record_id, "admission_record_id")
        require_opaque_id(self.proposal_id, "proposal_id")
        require_opaque_id(self.research_run_id, "research_run_id")
        require_aware_datetime(self.created_at, "created_at")
        if self.outcome not in ALLOWED_EVIDENCE_ADMISSION_OUTCOMES:
            raise PersistenceInputError("outcome is not an Evidence admission outcome")
        if not isinstance(self.reason_codes, tuple) or not self.reason_codes:
            raise PersistenceInputError("reason_codes must be a non-empty tuple")
        if not isinstance(self.observation_ids, tuple):
            raise PersistenceInputError("observation_ids must be a tuple")
        if not isinstance(self.assessment_ids, tuple):
            raise PersistenceInputError("assessment_ids must be a tuple")
        if not isinstance(self.admission_policy_version, str) or not self.admission_policy_version.strip():
            raise PersistenceInputError("admission_policy_version must be a non-empty string")
        if not isinstance(self.evaluator_version, str) or not self.evaluator_version.strip():
            raise PersistenceInputError("evaluator_version must be a non-empty string")
        if self.outcome == "ADMITTED":
            require_opaque_id(self.admitted_evidence_id, "admitted_evidence_id")
        elif self.admitted_evidence_id is not None:
            raise PersistenceInputError(
                "admitted_evidence_id must be null when Evidence is not admitted"
            )
        if self.polarity is not None and self.polarity not in ALLOWED_EVIDENCE_POLARITIES:
            raise PersistenceInputError("polarity is not an Evidence polarity")
        if self.claim_scope is not None and (
            not isinstance(self.claim_scope, str) or not self.claim_scope.strip()
        ):
            raise PersistenceInputError("claim_scope must be a non-empty string when set")


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
class ExecutionAttemptRecord:
    """Durable intended Worker invocation. Not a WorkerResult and not Evidence."""

    attempt_id: str
    request_id: str
    experiment_id: str
    research_run_id: str
    correlation_id: str
    worker_capability: str
    action: str
    target_reference: str
    budget_id: str
    side_effect_level: int
    authorization_decision_reference: str
    state: str
    created_at: datetime
    authorized_at: datetime | None = None
    dispatch_started_at: datetime | None = None
    completed_at: datetime | None = None

    def __post_init__(self) -> None:
        require_opaque_id(self.attempt_id, "attempt_id")
        require_opaque_id(self.request_id, "request_id")
        require_opaque_id(self.experiment_id, "experiment_id")
        require_opaque_id(self.research_run_id, "research_run_id")
        require_opaque_id(self.correlation_id, "correlation_id")
        require_opaque_id(self.worker_capability, "worker_capability")
        require_opaque_id(self.action, "action")
        require_opaque_id(self.target_reference, "target_reference")
        require_opaque_id(self.budget_id, "budget_id")
        require_opaque_id(
            self.authorization_decision_reference, "authorization_decision_reference"
        )
        require_aware_datetime(self.created_at, "created_at")
        if self.side_effect_level not in (0, 1, 2, 3):
            raise PersistenceInputError("side_effect_level must be 0, 1, 2, or 3")
        if self.state not in ALLOWED_EXECUTION_ATTEMPT_STATES:
            raise PersistenceInputError("state is not an ExecutionAttempt state")
        if self.authorized_at is not None:
            require_aware_datetime(self.authorized_at, "authorized_at")
        if self.dispatch_started_at is not None:
            require_aware_datetime(self.dispatch_started_at, "dispatch_started_at")
        if self.completed_at is not None:
            require_aware_datetime(self.completed_at, "completed_at")


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
