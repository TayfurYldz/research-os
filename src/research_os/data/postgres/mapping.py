"""Map spine tables to Data records. Adapter-only."""

from __future__ import annotations

from typing import Any, Mapping

from research_os.data.records import (
    ApprovalRecord,
    AuditEventRecord,
    AuthorizationSourceRecord,
    CandidateAdmissionRecord,
    CandidateRecord,
    DifferentialObservationRecord,
    EvidenceAdmissionRecord,
    EvidenceRecord,
    ExecutionAttemptRecord,
    ExperimentPlanRecord,
    ExperimentRecord,
    FindingProposalRecord,
    FindingRecord,
    HypothesisAssessmentRecord,
    HypothesisRecord,
    HumanReviewRecord,
    IssuedBudgetRecord,
    ObservationRecord,
    ProgramRecord,
    ResearchAdmissionRecord,
    ResearchReasoningRecord,
    ResearchRunRecord,
    TargetInferenceRecord,
    VerificationRecord,
    WorkerResultRecord,
    InvariantHypothesisRecord,
    InvariantCounterexampleRefRecord,
    ChainHypothesisRecord,
    ResearchOpportunityRecord,
    ResearchSelectionRecord,
    SnapshotRecord,
    SnapshotMemberRecord,
    ChangeEventRecord,
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


def execution_attempt_from_row(row: Mapping[str, Any]) -> ExecutionAttemptRecord:
    data = _mapping(row)
    return ExecutionAttemptRecord(
        attempt_id=data["attempt_id"],
        request_id=data["request_id"],
        experiment_id=data["experiment_id"],
        research_run_id=data["research_run_id"],
        correlation_id=data["correlation_id"],
        worker_capability=data["worker_capability"],
        action=data["action"],
        target_reference=data["target_reference"],
        budget_id=data["budget_id"],
        side_effect_level=data["side_effect_level"],
        authorization_decision_reference=data["authorization_decision_reference"],
        state=data["state"],
        created_at=data["created_at"],
        authorized_at=data.get("authorized_at"),
        dispatch_started_at=data.get("dispatch_started_at"),
        completed_at=data.get("completed_at"),
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


def research_reasoning_from_row(row: Mapping[str, Any]) -> ResearchReasoningRecord:
    data = _mapping(row)
    return ResearchReasoningRecord(
        reasoning_record_id=data["reasoning_record_id"],
        research_run_id=data["research_run_id"],
        hypothesis_id=data["hypothesis_id"],
        role=data["role"],
        adapter_identity=data["adapter_identity"],
        provider_adapter_identity=data["provider_adapter_identity"],
        correlation_id=data["correlation_id"],
        context_fingerprint=data["context_fingerprint"],
        structured_output=data["structured_output"],
        created_at=data["created_at"],
        model_id=data.get("model_id"),
        model_version=data.get("model_version"),
    )


def research_admission_from_row(row: Mapping[str, Any]) -> ResearchAdmissionRecord:
    data = _mapping(row)
    return ResearchAdmissionRecord(
        admission_record_id=data["admission_record_id"],
        research_run_id=data["research_run_id"],
        outcome=data["outcome"],
        reason=data["reason"],
        reason_code=data["reason_code"],
        context_fingerprint=data["context_fingerprint"],
        created_at=data["created_at"],
        generator_reasoning_record_id=data.get("generator_reasoning_record_id"),
        falsifier_reasoning_record_id=data.get("falsifier_reasoning_record_id"),
        admitted_hypothesis_id=data.get("admitted_hypothesis_id"),
    )


def experiment_plan_from_row(row: Mapping[str, Any]) -> ExperimentPlanRecord:
    data = _mapping(row)
    return ExperimentPlanRecord(
        experiment_id=data["experiment_id"],
        research_run_id=data["research_run_id"],
        hypothesis_id=data["hypothesis_id"],
        required_capability=data["required_capability"],
        action=data["action"],
        target_reference=data["target_reference"],
        side_effect_level=data["side_effect_level"],
        arguments=data["arguments"],
        requested_budget_id=data["requested_budget_id"],
        expected_observation=data["expected_observation"],
        disconfirming_observation=data["disconfirming_observation"],
        evaluation_strategy=data["evaluation_strategy"],
        created_at=data["created_at"],
    )


def hypothesis_assessment_from_row(row: Mapping[str, Any]) -> HypothesisAssessmentRecord:
    data = _mapping(row)
    observation_ids = data["observation_ids"]
    if isinstance(observation_ids, tuple):
        ids = observation_ids
    elif isinstance(observation_ids, list):
        ids = tuple(observation_ids)
    else:
        ids = ()
    return HypothesisAssessmentRecord(
        assessment_id=data["assessment_id"],
        hypothesis_id=data["hypothesis_id"],
        experiment_id=data["experiment_id"],
        research_run_id=data["research_run_id"],
        assessment_outcome=data["assessment_outcome"],
        observation_ids=ids,
        evaluator_kind=data["evaluator_kind"],
        evaluator_version=data["evaluator_version"],
        rationale=data["rationale"],
        evaluation_strategy=data["evaluation_strategy"],
        created_at=data["created_at"],
    )


def _id_tuple(value: object) -> tuple[str, ...]:
    if isinstance(value, tuple):
        return tuple(str(item) for item in value)
    if isinstance(value, list):
        return tuple(str(item) for item in value)
    return ()


def evidence_from_row(row: Mapping[str, Any]) -> EvidenceRecord:
    data = _mapping(row)
    return EvidenceRecord(
        evidence_id=data["evidence_id"],
        research_run_id=data["research_run_id"],
        hypothesis_id=data["hypothesis_id"],
        experiment_id=data["experiment_id"],
        admission_record_id=data["admission_record_id"],
        polarity=data["polarity"],
        claim_scope=data["claim_scope"],
        observation_ids=_id_tuple(data["observation_ids"]),
        assessment_ids=_id_tuple(data["assessment_ids"]),
        created_at=data["created_at"],
    )


def evidence_admission_from_row(row: Mapping[str, Any]) -> EvidenceAdmissionRecord:
    data = _mapping(row)
    return EvidenceAdmissionRecord(
        admission_record_id=data["admission_record_id"],
        proposal_id=data["proposal_id"],
        research_run_id=data["research_run_id"],
        outcome=data["outcome"],
        reason_codes=_id_tuple(data["reason_codes"]),
        observation_ids=_id_tuple(data["observation_ids"]),
        assessment_ids=_id_tuple(data["assessment_ids"]),
        admission_policy_version=data["admission_policy_version"],
        evaluator_version=data["evaluator_version"],
        created_at=data["created_at"],
        admitted_evidence_id=data.get("admitted_evidence_id"),
        claim_scope=data.get("claim_scope"),
        polarity=data.get("polarity"),
    )


def candidate_from_row(row: Mapping[str, Any]) -> CandidateRecord:
    data = _mapping(row)
    return CandidateRecord(
        candidate_id=data["candidate_id"],
        research_run_id=data["research_run_id"],
        hypothesis_id=data["hypothesis_id"],
        claim=data["claim"],
        classification=data["classification"],
        state=data["state"],
        evidence_ids=_id_tuple(data["evidence_ids"]),
        created_at=data["created_at"],
        admission_record_id=data["admission_record_id"],
    )


def candidate_admission_from_row(row: Mapping[str, Any]) -> CandidateAdmissionRecord:
    data = _mapping(row)
    return CandidateAdmissionRecord(
        admission_record_id=data["admission_record_id"],
        proposal_id=data["proposal_id"],
        research_run_id=data["research_run_id"],
        outcome=data["outcome"],
        reason_codes=_id_tuple(data["reason_codes"]),
        evidence_ids=_id_tuple(data["evidence_ids"]),
        admission_policy_version=data["admission_policy_version"],
        created_at=data["created_at"],
        admitted_candidate_id=data.get("admitted_candidate_id"),
        claim=data.get("claim"),
        classification=data.get("classification"),
    )


def verification_from_row(row: Mapping[str, Any]) -> VerificationRecord:
    data = _mapping(row)
    return VerificationRecord(
        verification_id=data["verification_id"],
        candidate_id=data["candidate_id"],
        research_run_id=data["research_run_id"],
        strategy=data["strategy"],
        outcome=data["outcome"],
        proposed_candidate_state=data["proposed_candidate_state"],
        original_evidence_ids=_id_tuple(data["original_evidence_ids"]),
        reproduction_evidence_ids=_id_tuple(data["reproduction_evidence_ids"]),
        negative_control_evidence_ids=_id_tuple(data["negative_control_evidence_ids"]),
        alternative_explanation_checks=dict(data["alternative_explanation_checks"] or {}),
        verifier_kind=data["verifier_kind"],
        verifier_identity=data["verifier_identity"],
        created_at=data["created_at"],
    )


def finding_proposal_from_row(row: Mapping[str, Any]) -> FindingProposalRecord:
    data = _mapping(row)
    return FindingProposalRecord(
        proposal_id=data["proposal_id"],
        candidate_id=data["candidate_id"],
        research_run_id=data["research_run_id"],
        title=data["title"],
        claim=data["claim"],
        classification=data["classification"],
        state=data["state"],
        evidence_ids=_id_tuple(data["evidence_ids"]),
        verification_ids=_id_tuple(data["verification_ids"]),
        content_fingerprint=data["content_fingerprint"],
        created_at=data["created_at"],
    )


def human_review_from_row(row: Mapping[str, Any]) -> HumanReviewRecord:
    data = _mapping(row)
    return HumanReviewRecord(
        review_id=data["review_id"],
        proposal_id=data["proposal_id"],
        content_fingerprint=data["content_fingerprint"],
        decision=data["decision"],
        reviewer_id=data["reviewer_id"],
        actor_type=data["actor_type"],
        reason_codes=_id_tuple(data["reason_codes"]),
        created_at=data["created_at"],
        note=data.get("note"),
    )


def approval_from_row(row: Mapping[str, Any]) -> ApprovalRecord:
    data = _mapping(row)
    return ApprovalRecord(
        approval_id=data["approval_id"],
        subject_reference=data["subject_reference"],
        decision=data["decision"],
        decided_by=data["decided_by"],
        actor_type=data["actor_type"],
        recorded=bool(data["recorded"]),
        created_at=data["created_at"],
        research_run_id=data["research_run_id"],
        proposal_id=data["proposal_id"],
        human_review_id=data["human_review_id"],
    )


def finding_from_row(row: Mapping[str, Any]) -> FindingRecord:
    data = _mapping(row)
    return FindingRecord(
        finding_id=data["finding_id"],
        finding_proposal_id=data["finding_proposal_id"],
        candidate_id=data["candidate_id"],
        research_run_id=data["research_run_id"],
        approval_id=data["approval_id"],
        human_review_id=data["human_review_id"],
        title=data["title"],
        claim=data["claim"],
        classification=data["classification"],
        evidence_ids=_id_tuple(data["evidence_ids"]),
        verification_ids=_id_tuple(data["verification_ids"]),
        created_at=data["created_at"],
    )


def target_inference_from_row(row: Mapping[str, Any]) -> TargetInferenceRecord:
    data = _mapping(row)
    return TargetInferenceRecord(
        inference_id=data["inference_id"],
        research_run_id=data["research_run_id"],
        kind=data["kind"],
        epistemic_status=data["epistemic_status"],
        opaque_ref=data["opaque_ref"],
        statement=data["statement"],
        source_refs=_id_tuple(data["source_refs"]),
        attributes=dict(data["attributes"] or {}),
        strategy_version=data["strategy_version"],
        created_at=data["created_at"],
    )


def differential_observation_from_row(row: Mapping[str, Any]) -> DifferentialObservationRecord:
    data = _mapping(row)
    return DifferentialObservationRecord(
        differential_id=data["differential_id"],
        research_run_id=data["research_run_id"],
        case_id=data["case_id"],
        baseline_observation_ids=_id_tuple(data["baseline_observation_ids"]),
        variant_observation_ids=_id_tuple(data["variant_observation_ids"]),
        changed_dimensions=_id_tuple(data["changed_dimensions"]),
        common_dimensions=_id_tuple(data["common_dimensions"]),
        observed_differences=dict(data["observed_differences"] or {}),
        observed_similarities=dict(data["observed_similarities"] or {}),
        interpretation=data["interpretation"],
        source_refs=_id_tuple(data["source_refs"]),
        strategy_version=data["strategy_version"],
        alternative_explanation_slots=_id_tuple(data["alternative_explanation_slots"]),
        created_at=data["created_at"],
    )


def invariant_hypothesis_from_row(row: Mapping[str, Any]) -> InvariantHypothesisRecord:
    data = _mapping(row)
    return InvariantHypothesisRecord(
        invariant_id=data["invariant_id"],
        research_run_id=data["research_run_id"],
        invariant_kind=data["invariant_kind"],
        status=data["status"],
        subject_refs=_id_tuple(data["subject_refs"]),
        expected_behavior=data["expected_behavior"],
        source_refs=_id_tuple(data["source_refs"]),
        applicability_context=dict(data["applicability_context"] or {}),
        assumptions=_id_tuple(data["assumptions"]),
        counterexample_refs=_id_tuple(data["counterexample_refs"]),
        falsification_direction=data["falsification_direction"],
        proposer_provenance=data["proposer_provenance"],
        strategy_version=data["strategy_version"],
        created_at=data["created_at"],
    )


def invariant_counterexample_from_row(
    row: Mapping[str, Any],
) -> InvariantCounterexampleRefRecord:
    data = _mapping(row)
    return InvariantCounterexampleRefRecord(
        counterexample_id=data["counterexample_id"],
        invariant_id=data["invariant_id"],
        source_ref=data["source_ref"],
        applicability_context=dict(data["applicability_context"] or {}),
        created_at=data["created_at"],
    )


def chain_hypothesis_from_row(row: Mapping[str, Any]) -> ChainHypothesisRecord:
    data = _mapping(row)
    steps = data["steps"] or []
    return ChainHypothesisRecord(
        chain_id=data["chain_id"],
        research_run_id=data["research_run_id"],
        structural_identity=data["structural_identity"],
        steps=tuple(dict(item) for item in steps),
        source_refs=_id_tuple(data["source_refs"]),
        preconditions=_id_tuple(data["preconditions"]),
        expected_resulting_capability=data["expected_resulting_capability"],
        unresolved_assumptions=_id_tuple(data["unresolved_assumptions"]),
        falsification_points=_id_tuple(data["falsification_points"]),
        descriptive_features=dict(data["descriptive_features"] or {}),
        strategy_version=data["strategy_version"],
        created_at=data["created_at"],
    )


def research_opportunity_from_row(row: Mapping[str, Any]) -> ResearchOpportunityRecord:
    data = _mapping(row)
    return ResearchOpportunityRecord(
        opportunity_id=data["opportunity_id"],
        research_run_id=data["research_run_id"],
        opportunity_kind=data["opportunity_kind"],
        mode=data["mode"],
        source_refs=_id_tuple(data["source_refs"]),
        proposed_direction=data["proposed_direction"],
        unresolved_question=data["unresolved_question"],
        expected_information_value_description=data[
            "expected_information_value_description"
        ],
        assumptions=_id_tuple(data["assumptions"]),
        dimensions=dict(data["dimensions"] or {}),
        context_signature=data["context_signature"],
        novelty_composition_marker=bool(data["novelty_composition_marker"]),
        prior_attempt_refs=_id_tuple(data["prior_attempt_refs"] or []),
        structural_identity=data["structural_identity"],
        strategy_version=data["strategy_version"],
        created_at=data["created_at"],
    )


def research_selection_from_row(row: Mapping[str, Any]) -> ResearchSelectionRecord:
    data = _mapping(row)
    return ResearchSelectionRecord(
        selection_id=data["selection_id"],
        research_run_id=data["research_run_id"],
        opportunity_id=data["opportunity_id"],
        outcome=data["outcome"],
        reason_codes=_id_tuple(data["reason_codes"]),
        structural_identity=data["structural_identity"],
        created_at=data["created_at"],
    )


def snapshot_from_row(row: Mapping[str, Any]) -> SnapshotRecord:
    data = _mapping(row)
    return SnapshotRecord(
        snapshot_id=data["snapshot_id"],
        research_run_id=data["research_run_id"],
        program_id=data["program_id"],
        target_identity=data["target_identity"],
        captured_at=data["captured_at"],
        strategy_version=data["strategy_version"],
        created_at=data["created_at"],
    )


def snapshot_member_from_row(row: Mapping[str, Any]) -> SnapshotMemberRecord:
    data = _mapping(row)
    return SnapshotMemberRecord(
        snapshot_id=data["snapshot_id"],
        observation_id=data["observation_id"],
        created_at=data["created_at"],
    )


def change_event_from_row(row: Mapping[str, Any]) -> ChangeEventRecord:
    data = _mapping(row)
    return ChangeEventRecord(
        change_event_id=data["change_event_id"],
        research_run_id=data["research_run_id"],
        baseline_snapshot_id=data["baseline_snapshot_id"],
        variant_snapshot_id=data["variant_snapshot_id"],
        category=data["category"],
        statement=data["statement"],
        source_refs=_id_tuple(data["source_refs"]),
        strategy_version=data["strategy_version"],
        created_at=data["created_at"],
    )
