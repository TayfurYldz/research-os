"""Map spine tables to Data records. Adapter-only."""

from __future__ import annotations

from typing import Any, Mapping

from research_os.data.records import (
    AuditEventRecord,
    AuthorizationSourceRecord,
    ExperimentRecord,
    HypothesisRecord,
    IssuedBudgetRecord,
    ObservationRecord,
    ProgramRecord,
    ResearchRunRecord,
    WorkerResultRecord,
)


def _mapping(row: Mapping[str, Any]) -> dict[str, Any]:
    return dict(row)


def program_from_row(row: Mapping[str, Any]) -> ProgramRecord:
    data = _mapping(row)
    return ProgramRecord(
        program_id=data["program_id"],
        created_at=data["created_at"],
        name=data.get("name"),
    )


def authorization_source_from_row(row: Mapping[str, Any]) -> AuthorizationSourceRecord:
    data = _mapping(row)
    return AuthorizationSourceRecord(
        authorization_source_id=data["authorization_source_id"],
        program_id=data["program_id"],
        state=data["state"],
        provenance_reference=data["provenance_reference"],
        created_at=data["created_at"],
        effective_from=data.get("effective_from"),
        effective_until=data.get("effective_until"),
    )


def research_run_from_row(row: Mapping[str, Any]) -> ResearchRunRecord:
    data = _mapping(row)
    return ResearchRunRecord(
        research_run_id=data["research_run_id"],
        program_id=data["program_id"],
        authorization_source_id=data["authorization_source_id"],
        initiated_by_actor_id=data["initiated_by_actor_id"],
        initiated_by_actor_type=data["initiated_by_actor_type"],
        started_at=data["started_at"],
    )


def issued_budget_from_row(row: Mapping[str, Any]) -> IssuedBudgetRecord:
    data = _mapping(row)
    return IssuedBudgetRecord(
        budget_id=data["budget_id"],
        research_run_id=data["research_run_id"],
        max_requests=data["max_requests"],
        max_tool_calls=data["max_tool_calls"],
        max_runtime_ms=data["max_runtime_ms"],
        max_concurrency=data["max_concurrency"],
        issued_at=data["issued_at"],
    )


def hypothesis_from_row(row: Mapping[str, Any]) -> HypothesisRecord:
    data = _mapping(row)
    return HypothesisRecord(
        hypothesis_id=data["hypothesis_id"],
        research_run_id=data["research_run_id"],
        claim=data["claim"],
        created_at=data["created_at"],
        origin_reference=data.get("origin_reference"),
    )


def experiment_from_row(row: Mapping[str, Any]) -> ExperimentRecord:
    data = _mapping(row)
    return ExperimentRecord(
        experiment_id=data["experiment_id"],
        research_run_id=data["research_run_id"],
        hypothesis_id=data["hypothesis_id"],
        budget_id=data["budget_id"],
        execution_state=data["execution_state"],
        created_at=data["created_at"],
    )


def worker_result_from_row(row: Mapping[str, Any]) -> WorkerResultRecord:
    data = _mapping(row)
    return WorkerResultRecord(
        worker_result_id=data["worker_result_id"],
        experiment_id=data["experiment_id"],
        research_run_id=data["research_run_id"],
        request_id=data["request_id"],
        correlation_id=data["correlation_id"],
        worker_capability=data["worker_capability"],
        action=data["action"],
        authorization_decision_reference=data["authorization_decision_reference"],
        budget_id=data["budget_id"],
        side_effect_level=data["side_effect_level"],
        contract_version=data["contract_version"],
        worker_id=data["worker_id"],
        status=data["status"],
        received_at=data["received_at"],
        started_at=data.get("started_at"),
        completed_at=data.get("completed_at"),
        parent_request_id=data.get("parent_request_id"),
        raw_result=data.get("raw_result"),
        raw_artifact_descriptors=data.get("raw_artifact_descriptors"),
        diagnostics=data.get("diagnostics"),
        control_signal=data.get("control_signal"),
    )


def observation_from_row(row: Mapping[str, Any]) -> ObservationRecord:
    data = _mapping(row)
    return ObservationRecord(
        observation_id=data["observation_id"],
        worker_result_id=data["worker_result_id"],
        observation_kind=data["observation_kind"],
        payload=data["payload"],
        normalization_version=data["normalization_version"],
        observed_at=data["observed_at"],
        created_at=data["created_at"],
    )


def audit_event_from_row(row: Mapping[str, Any]) -> AuditEventRecord:
    data = _mapping(row)
    return AuditEventRecord(
        audit_event_id=data["audit_event_id"],
        occurred_at=data["occurred_at"],
        actor_id=data["actor_id"],
        actor_type=data["actor_type"],
        event_type=data["event_type"],
        subject_type=data["subject_type"],
        subject_id=data["subject_id"],
        payload=data["payload"],
        correlation_id=data.get("correlation_id"),
    )
