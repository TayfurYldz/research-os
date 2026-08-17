"""SQLAlchemy Core metadata for the persistence spine. Adapter-only."""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    MetaData,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB

metadata = MetaData()

program = Table(
    "program",
    metadata,
    Column("program_id", Text, primary_key=True),
    Column("name", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

authorization_source = Table(
    "authorization_source",
    metadata,
    Column("authorization_source_id", Text, primary_key=True),
    Column("program_id", Text, ForeignKey("program.program_id"), nullable=False),
    Column("state", Text, nullable=False),
    Column("provenance_reference", Text, nullable=False),
    Column("effective_from", DateTime(timezone=True), nullable=True),
    Column("effective_until", DateTime(timezone=True), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint(
        "authorization_source_id",
        "program_id",
        name="uq_authorization_source_id_program",
    ),
    CheckConstraint(
        "state IN ('ACTIVE', 'EXPIRED', 'REVOKED')",
        name="ck_authorization_source_state",
    ),
    CheckConstraint(
        "effective_until IS NULL OR effective_from IS NULL "
        "OR effective_until >= effective_from",
        name="ck_authorization_source_effective_window",
    ),
)

research_run = Table(
    "research_run",
    metadata,
    Column("research_run_id", Text, primary_key=True),
    Column("program_id", Text, ForeignKey("program.program_id"), nullable=False),
    Column("authorization_source_id", Text, nullable=False),
    Column("initiated_by_actor_id", Text, nullable=False),
    Column("initiated_by_actor_type", Text, nullable=False),
    Column("started_at", DateTime(timezone=True), nullable=False),
    ForeignKeyConstraint(
        ["authorization_source_id", "program_id"],
        [
            "authorization_source.authorization_source_id",
            "authorization_source.program_id",
        ],
        name="fk_research_run_authorization_same_program",
    ),
    CheckConstraint(
        "initiated_by_actor_type IN "
        "('HUMAN_OPERATOR', 'CONTROL_PLANE', 'WORKER', 'INTEGRATION')",
        name="ck_research_run_actor_type",
    ),
)

issued_budget = Table(
    "issued_budget",
    metadata,
    Column("budget_id", Text, primary_key=True),
    Column("research_run_id", Text, ForeignKey("research_run.research_run_id"), nullable=False),
    Column("max_requests", Integer, nullable=False),
    Column("max_tool_calls", Integer, nullable=False),
    Column("max_runtime_ms", Integer, nullable=False),
    Column("max_concurrency", Integer, nullable=False),
    Column("issued_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("budget_id", "research_run_id", name="uq_issued_budget_id_run"),
    CheckConstraint("max_requests >= 0", name="ck_issued_budget_max_requests"),
    CheckConstraint("max_tool_calls >= 0", name="ck_issued_budget_max_tool_calls"),
    CheckConstraint("max_runtime_ms >= 0", name="ck_issued_budget_max_runtime_ms"),
    CheckConstraint("max_concurrency >= 0", name="ck_issued_budget_max_concurrency"),
)

hypothesis = Table(
    "hypothesis",
    metadata,
    Column("hypothesis_id", Text, primary_key=True),
    Column("research_run_id", Text, ForeignKey("research_run.research_run_id"), nullable=False),
    Column("claim", Text, nullable=False),
    Column("origin_reference", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("hypothesis_id", "research_run_id", name="uq_hypothesis_id_run"),
)

experiment = Table(
    "experiment",
    metadata,
    Column("experiment_id", Text, primary_key=True),
    Column("research_run_id", Text, nullable=False),
    Column("hypothesis_id", Text, nullable=False),
    Column("budget_id", Text, nullable=False),
    Column("execution_state", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    ForeignKeyConstraint(
        ["hypothesis_id", "research_run_id"],
        ["hypothesis.hypothesis_id", "hypothesis.research_run_id"],
        name="fk_experiment_hypothesis_same_run",
    ),
    ForeignKeyConstraint(
        ["budget_id", "research_run_id"],
        ["issued_budget.budget_id", "issued_budget.research_run_id"],
        name="fk_experiment_budget_same_run",
    ),
    UniqueConstraint("experiment_id", "research_run_id", name="uq_experiment_id_run"),
    CheckConstraint(
        "execution_state IN ("
        "'PLANNED', 'AUTHORIZATION_CHECK', 'READY', 'RUNNING', "
        "'EXECUTION_SUCCEEDED', 'EXECUTION_FAILED', 'BLOCKED', "
        "'CANCELLED', 'BUDGET_EXHAUSTED')",
        name="ck_experiment_execution_state",
    ),
)

execution_attempt = Table(
    "execution_attempt",
    metadata,
    Column("attempt_id", Text, primary_key=True),
    Column("request_id", Text, nullable=False),
    Column("experiment_id", Text, nullable=False),
    Column("research_run_id", Text, nullable=False),
    Column("correlation_id", Text, nullable=False),
    Column("worker_capability", Text, nullable=False),
    Column("action", Text, nullable=False),
    Column("target_reference", Text, nullable=False),
    Column("budget_id", Text, nullable=False),
    Column("side_effect_level", Integer, nullable=False),
    Column("authorization_decision_reference", Text, nullable=False),
    Column("state", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("authorized_at", DateTime(timezone=True), nullable=True),
    Column("dispatch_started_at", DateTime(timezone=True), nullable=True),
    Column("completed_at", DateTime(timezone=True), nullable=True),
    ForeignKeyConstraint(
        ["experiment_id", "research_run_id"],
        ["experiment.experiment_id", "experiment.research_run_id"],
        name="fk_execution_attempt_experiment_same_run",
    ),
    ForeignKeyConstraint(
        ["budget_id", "research_run_id"],
        ["issued_budget.budget_id", "issued_budget.research_run_id"],
        name="fk_execution_attempt_budget_same_run",
    ),
    ForeignKeyConstraint(
        ["authorization_decision_reference"],
        ["audit_event.audit_event_id"],
        name="fk_execution_attempt_authorization_decision",
    ),
    UniqueConstraint("request_id", name="uq_execution_attempt_request_id"),
    CheckConstraint(
        "state IN ("
        "'AUTHORIZED', 'DISPATCHING', 'COMPLETED', 'FAILED', "
        "'TIMED_OUT', 'CANCELLED', 'UNKNOWN_OUTCOME')",
        name="ck_execution_attempt_state",
    ),
    CheckConstraint(
        "side_effect_level IN (0, 1, 2, 3)",
        name="ck_execution_attempt_side_effect_level",
    ),
)

worker_result = Table(
    "worker_result",
    metadata,
    Column("worker_result_id", Text, primary_key=True),
    Column("experiment_id", Text, nullable=False),
    Column("research_run_id", Text, nullable=False),
    Column("request_id", Text, nullable=False),
    Column("correlation_id", Text, nullable=False),
    Column("parent_request_id", Text, nullable=True),
    Column("worker_capability", Text, nullable=False),
    Column("action", Text, nullable=False),
    Column("authorization_decision_reference", Text, nullable=False),
    Column("budget_id", Text, nullable=False),
    Column("side_effect_level", Integer, nullable=False),
    Column("contract_version", Text, nullable=False),
    Column("worker_id", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("started_at", DateTime(timezone=True), nullable=True),
    Column("completed_at", DateTime(timezone=True), nullable=True),
    Column("received_at", DateTime(timezone=True), nullable=False),
    Column("raw_result", JSONB, nullable=True),
    Column("raw_artifact_descriptors", JSONB, nullable=True),
    Column("diagnostics", JSONB, nullable=True),
    Column("control_signal", JSONB, nullable=True),
    ForeignKeyConstraint(
        ["experiment_id", "research_run_id"],
        ["experiment.experiment_id", "experiment.research_run_id"],
        name="fk_worker_result_experiment_same_run",
    ),
    ForeignKeyConstraint(
        ["budget_id", "research_run_id"],
        ["issued_budget.budget_id", "issued_budget.research_run_id"],
        name="fk_worker_result_budget_same_run",
    ),
    UniqueConstraint("request_id", name="uq_worker_result_request_id"),
    CheckConstraint(
        "status IN ("
        "'SUCCEEDED', 'EXECUTION_FAILED', 'BLOCKED', 'CANCELLED', "
        "'TIMED_OUT', 'BUDGET_EXHAUSTED', 'REAUTHORIZATION_REQUIRED')",
        name="ck_worker_result_status",
    ),
    CheckConstraint(
        "side_effect_level IN (0, 1, 2, 3)",
        name="ck_worker_result_side_effect_level",
    ),
)

observation = Table(
    "observation",
    metadata,
    Column("observation_id", Text, primary_key=True),
    Column(
        "worker_result_id",
        Text,
        ForeignKey("worker_result.worker_result_id"),
        nullable=False,
    ),
    Column("observation_kind", Text, nullable=False),
    Column("payload", JSONB, nullable=False),
    Column("normalization_version", Text, nullable=False),
    Column("observed_at", DateTime(timezone=True), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint(
        "worker_result_id",
        "observation_kind",
        "normalization_version",
        name="uq_observation_result_kind_version",
    ),
)

audit_event = Table(
    "audit_event",
    metadata,
    Column("audit_event_id", Text, primary_key=True),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
    Column("actor_id", Text, nullable=False),
    Column("actor_type", Text, nullable=False),
    Column("event_type", Text, nullable=False),
    Column("subject_type", Text, nullable=False),
    Column("subject_id", Text, nullable=False),
    Column("correlation_id", Text, nullable=True),
    Column("payload", JSONB, nullable=False),
    CheckConstraint(
        "actor_type IN "
        "('HUMAN_OPERATOR', 'CONTROL_PLANE', 'WORKER', 'INTEGRATION')",
        name="ck_audit_event_actor_type",
    ),
)

research_reasoning = Table(
    "research_reasoning",
    metadata,
    Column("reasoning_record_id", Text, primary_key=True),
    Column("research_run_id", Text, ForeignKey("research_run.research_run_id"), nullable=False),
    Column("hypothesis_id", Text, nullable=True),
    Column("role", Text, nullable=False),
    Column("adapter_identity", Text, nullable=False),
    Column("provider_adapter_identity", Text, nullable=False),
    Column("correlation_id", Text, nullable=False),
    Column("context_fingerprint", Text, nullable=False),
    Column("structured_output", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("model_id", Text, nullable=True),
    Column("model_version", Text, nullable=True),
    ForeignKeyConstraint(
        ["hypothesis_id", "research_run_id"],
        ["hypothesis.hypothesis_id", "hypothesis.research_run_id"],
        name="fk_research_reasoning_hypothesis_same_run",
    ),
    CheckConstraint(
        "role IN ('GENERATOR', 'FALSIFIER')",
        name="ck_research_reasoning_role",
    ),
)

research_admission = Table(
    "research_admission",
    metadata,
    Column("admission_record_id", Text, primary_key=True),
    Column("research_run_id", Text, ForeignKey("research_run.research_run_id"), nullable=False),
    Column("generator_reasoning_record_id", Text, nullable=True),
    Column("falsifier_reasoning_record_id", Text, nullable=True),
    Column("outcome", Text, nullable=False),
    Column("admitted_hypothesis_id", Text, nullable=True),
    Column("reason", Text, nullable=False),
    Column("reason_code", Text, nullable=False),
    Column("context_fingerprint", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    ForeignKeyConstraint(
        ["generator_reasoning_record_id"],
        ["research_reasoning.reasoning_record_id"],
        name="fk_research_admission_generator_reasoning",
    ),
    ForeignKeyConstraint(
        ["falsifier_reasoning_record_id"],
        ["research_reasoning.reasoning_record_id"],
        name="fk_research_admission_falsifier_reasoning",
    ),
    ForeignKeyConstraint(
        ["admitted_hypothesis_id", "research_run_id"],
        ["hypothesis.hypothesis_id", "hypothesis.research_run_id"],
        name="fk_research_admission_hypothesis_same_run",
    ),
    CheckConstraint(
        "outcome IN ("
        "'ADMITTED', 'REJECTED_UNTESTABLE', 'REJECTED_UNSUPPORTED', "
        "'REJECTED_POLICY_CONFLICT', 'NEEDS_MORE_CONTEXT', 'MODEL_INVOCATION_FAILED')",
        name="ck_research_admission_outcome",
    ),
    CheckConstraint(
        "(outcome = 'ADMITTED' AND admitted_hypothesis_id IS NOT NULL) OR "
        "(outcome <> 'ADMITTED' AND admitted_hypothesis_id IS NULL)",
        name="ck_research_admission_hypothesis_presence",
    ),
)

experiment_plan = Table(
    "experiment_plan",
    metadata,
    Column("experiment_id", Text, primary_key=True),
    Column("research_run_id", Text, nullable=False),
    Column("hypothesis_id", Text, nullable=False),
    Column("required_capability", Text, nullable=False),
    Column("action", Text, nullable=False),
    Column("target_reference", Text, nullable=False),
    Column("side_effect_level", Integer, nullable=False),
    Column("arguments", JSONB, nullable=False),
    Column("requested_budget_id", Text, nullable=False),
    Column("expected_observation", Text, nullable=False),
    Column("disconfirming_observation", Text, nullable=False),
    Column("evaluation_strategy", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    ForeignKeyConstraint(
        ["experiment_id", "research_run_id"],
        ["experiment.experiment_id", "experiment.research_run_id"],
        name="fk_experiment_plan_experiment_same_run",
    ),
    ForeignKeyConstraint(
        ["hypothesis_id", "research_run_id"],
        ["hypothesis.hypothesis_id", "hypothesis.research_run_id"],
        name="fk_experiment_plan_hypothesis_same_run",
    ),
    ForeignKeyConstraint(
        ["requested_budget_id", "research_run_id"],
        ["issued_budget.budget_id", "issued_budget.research_run_id"],
        name="fk_experiment_plan_budget_same_run",
    ),
    UniqueConstraint("experiment_id", "research_run_id", name="uq_experiment_plan_id_run"),
    CheckConstraint(
        "side_effect_level IN (0, 1, 2, 3)",
        name="ck_experiment_plan_side_effect_level",
    ),
)

hypothesis_assessment = Table(
    "hypothesis_assessment",
    metadata,
    Column("assessment_id", Text, primary_key=True),
    Column("hypothesis_id", Text, nullable=False),
    Column("experiment_id", Text, nullable=False),
    Column("research_run_id", Text, nullable=False),
    Column("assessment_outcome", Text, nullable=False),
    Column("observation_ids", JSONB, nullable=False),
    Column("evaluator_kind", Text, nullable=False),
    Column("evaluator_version", Text, nullable=False),
    Column("rationale", JSONB, nullable=False),
    Column("evaluation_strategy", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    ForeignKeyConstraint(
        ["hypothesis_id", "research_run_id"],
        ["hypothesis.hypothesis_id", "hypothesis.research_run_id"],
        name="fk_hypothesis_assessment_hypothesis_same_run",
    ),
    ForeignKeyConstraint(
        ["experiment_id", "research_run_id"],
        ["experiment.experiment_id", "experiment.research_run_id"],
        name="fk_hypothesis_assessment_experiment_same_run",
    ),
    CheckConstraint(
        "assessment_outcome IN ("
        "'CONSISTENT_WITH_PREDICTION', 'CONTRADICTS_PREDICTION', "
        "'INCONCLUSIVE', 'EXECUTION_UNUSABLE', 'NEEDS_MORE_CONTEXT')",
        name="ck_hypothesis_assessment_outcome",
    ),
    CheckConstraint(
        "evaluator_kind IN ('DETERMINISTIC')",
        name="ck_hypothesis_assessment_evaluator_kind",
    ),
)

evidence = Table(
    "evidence",
    metadata,
    Column("evidence_id", Text, primary_key=True),
    Column("research_run_id", Text, ForeignKey("research_run.research_run_id"), nullable=False),
    Column("hypothesis_id", Text, nullable=False),
    Column("experiment_id", Text, nullable=False),
    Column("admission_record_id", Text, nullable=False),
    Column("polarity", Text, nullable=False),
    Column("claim_scope", Text, nullable=False),
    Column("observation_ids", JSONB, nullable=False),
    Column("assessment_ids", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    ForeignKeyConstraint(
        ["hypothesis_id", "research_run_id"],
        ["hypothesis.hypothesis_id", "hypothesis.research_run_id"],
        name="fk_evidence_hypothesis_same_run",
    ),
    ForeignKeyConstraint(
        ["experiment_id", "research_run_id"],
        ["experiment.experiment_id", "experiment.research_run_id"],
        name="fk_evidence_experiment_same_run",
    ),
    CheckConstraint(
        "polarity IN ('SUPPORTING', 'CONTRADICTING', 'NEUTRAL')",
        name="ck_evidence_polarity",
    ),
)

evidence_observation = Table(
    "evidence_observation",
    metadata,
    Column("evidence_id", Text, ForeignKey("evidence.evidence_id"), primary_key=True),
    Column("observation_id", Text, ForeignKey("observation.observation_id"), primary_key=True),
)

evidence_admission = Table(
    "evidence_admission",
    metadata,
    Column("admission_record_id", Text, primary_key=True),
    Column("proposal_id", Text, nullable=False),
    Column("research_run_id", Text, ForeignKey("research_run.research_run_id"), nullable=False),
    Column("outcome", Text, nullable=False),
    Column("reason_codes", JSONB, nullable=False),
    Column("observation_ids", JSONB, nullable=False),
    Column("assessment_ids", JSONB, nullable=False),
    Column("admission_policy_version", Text, nullable=False),
    Column("evaluator_version", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("admitted_evidence_id", Text, ForeignKey("evidence.evidence_id"), nullable=True),
    Column("claim_scope", Text, nullable=True),
    Column("polarity", Text, nullable=True),
    CheckConstraint(
        "outcome IN ("
        "'ADMITTED', 'REJECTED_INSUFFICIENT_SUPPORT', 'REJECTED_BROKEN_PROVENANCE', "
        "'REJECTED_EXECUTION_UNUSABLE', 'REJECTED_POLICY_CONFLICT', 'NEEDS_VERIFICATION')",
        name="ck_evidence_admission_outcome",
    ),
    CheckConstraint(
        "(outcome = 'ADMITTED' AND admitted_evidence_id IS NOT NULL) OR "
        "(outcome <> 'ADMITTED' AND admitted_evidence_id IS NULL)",
        name="ck_evidence_admission_evidence_presence",
    ),
    CheckConstraint(
        "polarity IS NULL OR polarity IN ('SUPPORTING', 'CONTRADICTING', 'NEUTRAL')",
        name="ck_evidence_admission_polarity",
    ),
)

candidate = Table(
    "candidate",
    metadata,
    Column("candidate_id", Text, primary_key=True),
    Column("research_run_id", Text, ForeignKey("research_run.research_run_id"), nullable=False),
    Column("hypothesis_id", Text, nullable=False),
    Column("claim", Text, nullable=False),
    Column("classification", Text, nullable=False),
    Column("state", Text, nullable=False),
    Column("evidence_ids", JSONB, nullable=False),
    Column("admission_record_id", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    ForeignKeyConstraint(
        ["hypothesis_id", "research_run_id"],
        ["hypothesis.hypothesis_id", "hypothesis.research_run_id"],
        name="fk_candidate_hypothesis_same_run",
    ),
    CheckConstraint(
        "state IN ("
        "'OPEN', 'VERIFYING', 'VALIDATED', 'REJECTED', "
        "'INCONCLUSIVE', 'DUPLICATE', 'OUT_OF_SCOPE')",
        name="ck_candidate_state",
    ),
    CheckConstraint(
        "classification IN ('DIAGNOSTIC_PLUMBING', 'HTTP_AUTHORIZATION_DIFFERENTIAL', 'HTTP_STATE_TRANSITION_AUTHORIZATION')",
        name="ck_candidate_classification",
    ),
)

candidate_evidence = Table(
    "candidate_evidence",
    metadata,
    Column("candidate_id", Text, ForeignKey("candidate.candidate_id"), primary_key=True),
    Column("evidence_id", Text, ForeignKey("evidence.evidence_id"), primary_key=True),
)

candidate_admission = Table(
    "candidate_admission",
    metadata,
    Column("admission_record_id", Text, primary_key=True),
    Column("proposal_id", Text, nullable=False),
    Column("research_run_id", Text, ForeignKey("research_run.research_run_id"), nullable=False),
    Column("outcome", Text, nullable=False),
    Column("reason_codes", JSONB, nullable=False),
    Column("evidence_ids", JSONB, nullable=False),
    Column("admission_policy_version", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("admitted_candidate_id", Text, ForeignKey("candidate.candidate_id"), nullable=True),
    Column("claim", Text, nullable=True),
    Column("classification", Text, nullable=True),
    CheckConstraint(
        "outcome IN ("
        "'ADMITTED', 'REJECTED_INSUFFICIENT_SUPPORT', 'REJECTED_BROKEN_PROVENANCE', "
        "'REJECTED_CLAIM_EXCEEDS_EVIDENCE', 'REJECTED_NOT_TESTABLE', "
        "'REJECTED_POLICY_CONFLICT')",
        name="ck_candidate_admission_outcome",
    ),
    CheckConstraint(
        "(outcome = 'ADMITTED' AND admitted_candidate_id IS NOT NULL) OR "
        "(outcome <> 'ADMITTED' AND admitted_candidate_id IS NULL)",
        name="ck_candidate_admission_candidate_presence",
    ),
    CheckConstraint(
        "classification IS NULL OR classification IN ('DIAGNOSTIC_PLUMBING', 'HTTP_AUTHORIZATION_DIFFERENTIAL', 'HTTP_STATE_TRANSITION_AUTHORIZATION')",
        name="ck_candidate_admission_classification",
    ),
)

verification = Table(
    "verification",
    metadata,
    Column("verification_id", Text, primary_key=True),
    Column("candidate_id", Text, ForeignKey("candidate.candidate_id"), nullable=False),
    Column("research_run_id", Text, ForeignKey("research_run.research_run_id"), nullable=False),
    Column("strategy", Text, nullable=False),
    Column("outcome", Text, nullable=False),
    Column("proposed_candidate_state", Text, nullable=False),
    Column("original_evidence_ids", JSONB, nullable=False),
    Column("reproduction_evidence_ids", JSONB, nullable=False),
    Column("negative_control_evidence_ids", JSONB, nullable=False),
    Column("alternative_explanation_checks", JSONB, nullable=False),
    Column("verifier_kind", Text, nullable=False),
    Column("verifier_identity", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    CheckConstraint(
        "outcome IN ("
        "'VALIDATED', 'REJECTED', 'INCONCLUSIVE', 'DUPLICATE', 'OUT_OF_SCOPE')",
        name="ck_verification_outcome",
    ),
    CheckConstraint(
        "proposed_candidate_state IN ("
        "'OPEN', 'VERIFYING', 'VALIDATED', 'REJECTED', "
        "'INCONCLUSIVE', 'DUPLICATE', 'OUT_OF_SCOPE')",
        name="ck_verification_proposed_state",
    ),
    CheckConstraint(
        "proposed_candidate_state = outcome",
        name="ck_verification_proposed_matches_outcome",
    ),
    CheckConstraint(
        "verifier_kind IN ('DETERMINISTIC')",
        name="ck_verification_verifier_kind",
    ),
)

finding_proposal = Table(
    "finding_proposal",
    metadata,
    Column("proposal_id", Text, primary_key=True),
    Column("candidate_id", Text, ForeignKey("candidate.candidate_id"), nullable=False),
    Column("research_run_id", Text, ForeignKey("research_run.research_run_id"), nullable=False),
    Column("title", Text, nullable=False),
    Column("claim", Text, nullable=False),
    Column("classification", Text, nullable=False),
    Column("state", Text, nullable=False),
    Column("evidence_ids", JSONB, nullable=False),
    Column("verification_ids", JSONB, nullable=False),
    Column("content_fingerprint", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    CheckConstraint(
        "state IN ('PROPOSED', 'HUMAN_REVIEW', 'APPROVED', 'REJECTED')",
        name="ck_finding_proposal_state",
    ),
    CheckConstraint(
        "classification IN ('DIAGNOSTIC_PLUMBING', 'HTTP_AUTHORIZATION_DIFFERENTIAL', 'HTTP_STATE_TRANSITION_AUTHORIZATION')",
        name="ck_finding_proposal_classification",
    ),
)

human_review = Table(
    "human_review",
    metadata,
    Column("review_id", Text, primary_key=True),
    Column("proposal_id", Text, ForeignKey("finding_proposal.proposal_id"), nullable=False),
    Column("content_fingerprint", Text, nullable=False),
    Column("decision", Text, nullable=False),
    Column("reviewer_id", Text, nullable=False),
    Column("actor_type", Text, nullable=False),
    Column("reason_codes", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("note", Text, nullable=True),
    UniqueConstraint("proposal_id", "content_fingerprint", name="uq_human_review_proposal_fingerprint"),
    CheckConstraint(
        "decision IN ('APPROVE', 'REJECT')",
        name="ck_human_review_decision",
    ),
    CheckConstraint(
        "actor_type IN ('HUMAN_OPERATOR', 'CONTROL_PLANE', 'WORKER', 'INTEGRATION')",
        name="ck_human_review_actor_type",
    ),
)

approval = Table(
    "approval",
    metadata,
    Column("approval_id", Text, primary_key=True),
    Column("subject_reference", Text, nullable=False),
    Column("decision", Text, nullable=False),
    Column("decided_by", Text, nullable=False),
    Column("actor_type", Text, nullable=False),
    Column("recorded", Boolean, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("research_run_id", Text, ForeignKey("research_run.research_run_id"), nullable=False),
    Column("proposal_id", Text, ForeignKey("finding_proposal.proposal_id"), nullable=False),
    Column("human_review_id", Text, ForeignKey("human_review.review_id"), nullable=False),
    UniqueConstraint("subject_reference", name="uq_approval_subject_reference"),
    CheckConstraint(
        "decision IN ('APPROVE', 'REJECT')",
        name="ck_approval_decision",
    ),
    CheckConstraint(
        "actor_type IN ('HUMAN_OPERATOR', 'CONTROL_PLANE', 'WORKER', 'INTEGRATION')",
        name="ck_approval_actor_type",
    ),
    CheckConstraint("recorded IS TRUE", name="ck_approval_recorded"),
)

finding = Table(
    "finding",
    metadata,
    Column("finding_id", Text, primary_key=True),
    Column("finding_proposal_id", Text, ForeignKey("finding_proposal.proposal_id"), nullable=False),
    Column("candidate_id", Text, ForeignKey("candidate.candidate_id"), nullable=False),
    Column("research_run_id", Text, ForeignKey("research_run.research_run_id"), nullable=False),
    Column("approval_id", Text, ForeignKey("approval.approval_id"), nullable=False),
    Column("human_review_id", Text, ForeignKey("human_review.review_id"), nullable=False),
    Column("title", Text, nullable=False),
    Column("claim", Text, nullable=False),
    Column("classification", Text, nullable=False),
    Column("evidence_ids", JSONB, nullable=False),
    Column("verification_ids", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("finding_proposal_id", name="uq_finding_proposal_id"),
    CheckConstraint(
        "classification IN ('DIAGNOSTIC_PLUMBING', 'HTTP_AUTHORIZATION_DIFFERENTIAL', 'HTTP_STATE_TRANSITION_AUTHORIZATION')",
        name="ck_finding_classification",
    ),
)

target_inference = Table(
    "target_inference",
    metadata,
    Column("inference_id", Text, primary_key=True),
    Column("research_run_id", Text, ForeignKey("research_run.research_run_id"), nullable=False),
    Column("kind", Text, nullable=False),
    Column("epistemic_status", Text, nullable=False),
    Column("opaque_ref", Text, nullable=False),
    Column("statement", Text, nullable=False),
    Column("source_refs", JSONB, nullable=False),
    Column("attributes", JSONB, nullable=False),
    Column("strategy_version", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    CheckConstraint(
        "epistemic_status IN ('INFERRED', 'HYPOTHESIZED')",
        name="ck_target_inference_epistemic_status",
    ),
    CheckConstraint(
        "kind IN ('ACTOR', 'ROLE', 'SESSION', 'RESOURCE', 'ACTION', 'STATE', "
        "'RELATIONSHIP', 'STATE_TRANSITION')",
        name="ck_target_inference_kind",
    ),
)

differential_observation = Table(
    "differential_observation",
    metadata,
    Column("differential_id", Text, primary_key=True),
    Column("research_run_id", Text, ForeignKey("research_run.research_run_id"), nullable=False),
    Column("case_id", Text, nullable=False),
    Column("baseline_observation_ids", JSONB, nullable=False),
    Column("variant_observation_ids", JSONB, nullable=False),
    Column("changed_dimensions", JSONB, nullable=False),
    Column("common_dimensions", JSONB, nullable=False),
    Column("observed_differences", JSONB, nullable=False),
    Column("observed_similarities", JSONB, nullable=False),
    Column("interpretation", Text, nullable=False),
    Column("source_refs", JSONB, nullable=False),
    Column("strategy_version", Text, nullable=False),
    Column("alternative_explanation_slots", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    CheckConstraint(
        "interpretation IN ('CONTROLLED_DIFFERENCE', 'EQUIVALENT', 'INCOMPARABLE')",
        name="ck_differential_interpretation",
    ),
)

invariant_hypothesis = Table(
    "invariant_hypothesis",
    metadata,
    Column("invariant_id", Text, primary_key=True),
    Column("research_run_id", Text, ForeignKey("research_run.research_run_id"), nullable=False),
    Column("invariant_kind", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("subject_refs", JSONB, nullable=False),
    Column("expected_behavior", Text, nullable=False),
    Column("source_refs", JSONB, nullable=False),
    Column("applicability_context", JSONB, nullable=False),
    Column("assumptions", JSONB, nullable=False),
    Column("counterexample_refs", JSONB, nullable=False),
    Column("falsification_direction", Text, nullable=False),
    Column("proposer_provenance", Text, nullable=False),
    Column("strategy_version", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    CheckConstraint(
        "status IN ('TESTABLE', 'CHALLENGED', 'RETIRED')",
        name="ck_invariant_hypothesis_status",
    ),
    CheckConstraint(
        "invariant_kind IN ("
        "'ACCESS_RELATION', 'STATE_TRANSITION', 'OWNERSHIP_RELATION', "
        "'ROLE_BOUNDARY', 'SESSION_BINDING', 'RESOURCE_ISOLATION', "
        "'IMMUTABILITY_AFTER_STATE', 'SEQUENCE_PRECONDITION', "
        "'INPUT_OUTPUT_RELATION', 'OTHER')",
        name="ck_invariant_hypothesis_kind",
    ),
)

invariant_source_ref = Table(
    "invariant_source_ref",
    metadata,
    Column("invariant_id", Text, ForeignKey("invariant_hypothesis.invariant_id"), primary_key=True),
    Column("source_ref", Text, primary_key=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

invariant_counterexample_ref = Table(
    "invariant_counterexample_ref",
    metadata,
    Column("counterexample_id", Text, primary_key=True),
    Column(
        "invariant_id",
        Text,
        ForeignKey("invariant_hypothesis.invariant_id"),
        nullable=False,
    ),
    Column("source_ref", Text, nullable=False),
    Column("applicability_context", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

chain_hypothesis = Table(
    "chain_hypothesis",
    metadata,
    Column("chain_id", Text, primary_key=True),
    Column("research_run_id", Text, ForeignKey("research_run.research_run_id"), nullable=False),
    Column("structural_identity", Text, nullable=False),
    Column("steps", JSONB, nullable=False),
    Column("source_refs", JSONB, nullable=False),
    Column("preconditions", JSONB, nullable=False),
    Column("expected_resulting_capability", Text, nullable=False),
    Column("unresolved_assumptions", JSONB, nullable=False),
    Column("falsification_points", JSONB, nullable=False),
    Column("descriptive_features", JSONB, nullable=False),
    Column("strategy_version", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint(
        "research_run_id",
        "structural_identity",
        name="uq_chain_hypothesis_run_identity",
    ),
)

research_opportunity = Table(
    "research_opportunity",
    metadata,
    Column("opportunity_id", Text, primary_key=True),
    Column("research_run_id", Text, ForeignKey("research_run.research_run_id"), nullable=False),
    Column("opportunity_kind", Text, nullable=False),
    Column("mode", Text, nullable=False),
    Column("source_refs", JSONB, nullable=False),
    Column("proposed_direction", Text, nullable=False),
    Column("unresolved_question", Text, nullable=False),
    Column("expected_information_value_description", Text, nullable=False),
    Column("assumptions", JSONB, nullable=False),
    Column("dimensions", JSONB, nullable=False),
    Column("context_signature", Text, nullable=False),
    Column("novelty_composition_marker", Boolean, nullable=False),
    Column("prior_attempt_refs", JSONB, nullable=False),
    Column("structural_identity", Text, nullable=False),
    Column("strategy_version", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    CheckConstraint("mode IN ('EXPLORATION', 'EXPLOITATION')", name="ck_research_opportunity_mode"),
    UniqueConstraint(
        "research_run_id",
        "structural_identity",
        name="uq_research_opportunity_run_identity",
    ),
)

research_selection = Table(
    "research_selection",
    metadata,
    Column("selection_id", Text, primary_key=True),
    Column("research_run_id", Text, ForeignKey("research_run.research_run_id"), nullable=False),
    Column("opportunity_id", Text, nullable=False),
    Column("outcome", Text, nullable=False),
    Column("reason_codes", JSONB, nullable=False),
    Column("structural_identity", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    CheckConstraint(
        "outcome IN ("
        "'SELECT', 'DEFER', 'SKIP_DUPLICATE', 'SKIP_LOW_INFORMATION', "
        "'BLOCKED_BUDGET', 'BLOCKED_POLICY', 'NEEDS_MORE_CONTEXT')",
        name="ck_research_selection_outcome",
    ),
)

snapshot = Table(
    "snapshot",
    metadata,
    Column("snapshot_id", Text, primary_key=True),
    Column("research_run_id", Text, ForeignKey("research_run.research_run_id"), nullable=False),
    Column("program_id", Text, ForeignKey("program.program_id"), nullable=False),
    Column("target_identity", Text, nullable=False),
    Column("captured_at", DateTime(timezone=True), nullable=False),
    Column("strategy_version", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

snapshot_member = Table(
    "snapshot_member",
    metadata,
    Column("snapshot_id", Text, ForeignKey("snapshot.snapshot_id"), primary_key=True),
    Column("observation_id", Text, ForeignKey("observation.observation_id"), primary_key=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

change_event = Table(
    "change_event",
    metadata,
    Column("change_event_id", Text, primary_key=True),
    Column("research_run_id", Text, ForeignKey("research_run.research_run_id"), nullable=False),
    Column("baseline_snapshot_id", Text, ForeignKey("snapshot.snapshot_id"), nullable=False),
    Column("variant_snapshot_id", Text, ForeignKey("snapshot.snapshot_id"), nullable=False),
    Column("category", Text, nullable=False),
    Column("statement", Text, nullable=False),
    Column("source_refs", JSONB, nullable=False),
    Column("strategy_version", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    CheckConstraint(
        "category IN ("
        "'ADDED', 'REMOVED', 'MODIFIED', 'RELATION_CHANGED', "
        "'STATE_CHANGED', 'BEHAVIOR_CHANGED', 'UNKNOWN_CHANGE')",
        name="ck_change_event_category",
    ),
)

research_orchestration = Table(
    "research_orchestration",
    metadata,
    Column("research_run_id", Text, ForeignKey("research_run.research_run_id"), primary_key=True),
    Column("state", Text, nullable=False),
    Column("cycle_number", Integer, nullable=False),
    Column("last_phase", Text, nullable=False),
    Column("last_opportunity_id", Text, nullable=True),
    Column("last_hypothesis_id", Text, nullable=True),
    Column("last_experiment_id", Text, nullable=True),
    Column("pause_reason", Text, nullable=True),
    Column("stop_reason", Text, nullable=True),
    Column("policy_version", Text, nullable=False),
    Column("max_cycles", Integer, nullable=False),
    Column("max_experiments", Integer, nullable=False),
    Column("max_model_calls", Integer, nullable=False),
    Column("max_worker_invocations", Integer, nullable=False),
    Column("max_elapsed_ms", Integer, nullable=False),
    Column("max_selected_opportunities", Integer, nullable=False),
    Column("max_runtime_fallback", Integer, nullable=False),
    Column("side_effect_ceiling", Integer, nullable=False),
    Column("allow_repeated_control_experiments", Boolean, nullable=False),
    Column("budget_id", Text, nullable=False),
    Column("target_reference", Text, nullable=False),
    Column("research_question", Text, nullable=False),
    Column("configuration_fingerprint", Text, nullable=False),
    Column("current_phase", Text, nullable=False),
    Column("active_cycle_id", Text, nullable=True),
    Column("last_attempt_id", Text, nullable=True),
    Column("last_observation_id", Text, nullable=True),
    Column("last_assessment_id", Text, nullable=True),
    Column("last_worker_result_id", Text, nullable=True),
    Column("routing_policy_version", Text, nullable=True),
    Column("scope_fingerprint", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("checkpoint_at", DateTime(timezone=True), nullable=False),
    CheckConstraint(
        "state IN ("
        "'READY', 'RUNNING', 'PAUSED', 'WAITING_HUMAN', 'BLOCKED', "
        "'BUDGET_EXHAUSTED', 'COMPLETED', 'FAILED_OPERATIONAL')",
        name="ck_research_orchestration_state",
    ),
    CheckConstraint("cycle_number >= 0", name="ck_research_orchestration_cycle_number"),
    CheckConstraint("max_cycles >= 0", name="ck_research_orchestration_max_cycles"),
    CheckConstraint("max_experiments >= 0", name="ck_research_orchestration_max_experiments"),
    CheckConstraint("max_model_calls >= 0", name="ck_research_orchestration_max_model_calls"),
    CheckConstraint(
        "max_worker_invocations >= 0",
        name="ck_research_orchestration_max_worker_invocations",
    ),
    CheckConstraint("max_elapsed_ms >= 0", name="ck_research_orchestration_max_elapsed_ms"),
    CheckConstraint(
        "max_selected_opportunities >= 0",
        name="ck_research_orchestration_max_selected_opportunities",
    ),
    CheckConstraint(
        "max_runtime_fallback >= 0",
        name="ck_research_orchestration_max_runtime_fallback",
    ),
    CheckConstraint(
        "side_effect_ceiling IN (0, 1, 2, 3)",
        name="ck_research_orchestration_side_effect_ceiling",
    ),
    CheckConstraint(
        "current_phase IN ("
        "'CYCLE_READY', 'OPPORTUNITY_SELECTED', 'HYPOTHESIS_ADMITTED', "
        "'EXPERIMENT_PLANNED', 'AUTHORIZATION_REQUESTED', 'ATTEMPT_AUTHORIZED', "
        "'DISPATCHING', 'WORKER_RESULT_RECORDED', 'TRANSITION_A_COMPLETE', "
        "'ASSESSMENT_COMPLETE', 'TRANSITION_B_COMPLETE', 'CYCLE_COMPLETE')",
        name="ck_research_orchestration_current_phase",
    ),
)

research_cycle = Table(
    "research_cycle",
    metadata,
    Column("cycle_id", Text, primary_key=True),
    Column("research_run_id", Text, ForeignKey("research_run.research_run_id"), nullable=False),
    Column("cycle_number", Integer, nullable=False),
    Column("phase_completed", Text, nullable=False),
    Column("outcome", Text, nullable=False),
    Column("stop_reason", Text, nullable=True),
    Column("opportunity_id", Text, nullable=True),
    Column("hypothesis_id", Text, nullable=True),
    Column("experiment_id", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint(
        "research_run_id",
        "cycle_number",
        name="uq_research_cycle_run_number",
    ),
    CheckConstraint("cycle_number >= 0", name="ck_research_cycle_number"),
    CheckConstraint(
        "outcome IN ("
        "'CONTINUE', 'PAUSE', 'COMPLETE', 'BLOCKED', 'REQUIRE_HUMAN_REVIEW')",
        name="ck_research_cycle_outcome",
    ),
)

budget_consumption = Table(
    "budget_consumption",
    metadata,
    Column("consumption_id", Text, primary_key=True),
    Column("budget_id", Text, nullable=False),
    Column("research_run_id", Text, nullable=False),
    Column("experiment_id", Text, nullable=True),
    Column("request_id", Text, nullable=True),
    Column("resource_type", Text, nullable=False),
    Column("amount", Integer, nullable=False),
    Column("unit", Text, nullable=False),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
    Column("provenance", Text, nullable=False),
    ForeignKeyConstraint(
        ["budget_id", "research_run_id"],
        ["issued_budget.budget_id", "issued_budget.research_run_id"],
        name="fk_budget_consumption_issued_budget_same_run",
    ),
    UniqueConstraint(
        "budget_id",
        "request_id",
        "resource_type",
        name="uq_budget_consumption_request_resource",
    ),
    CheckConstraint("amount > 0", name="ck_budget_consumption_amount_positive"),
    CheckConstraint(
        "resource_type IN ("
        "'MODEL_CALL', 'WORKER_INVOCATION', 'REQUEST', "
        "'EXECUTION_TIME', 'ARTIFACT_BYTES', 'COST')",
        name="ck_budget_consumption_resource_type",
    ),
    CheckConstraint(
        "unit IN ('count', 'milliseconds', 'bytes')",
        name="ck_budget_consumption_unit",
    ),
)

SPINE_TABLES = (
    program,
    authorization_source,
    research_run,
    issued_budget,
    hypothesis,
    experiment,
    execution_attempt,
    worker_result,
    observation,
    audit_event,
    research_reasoning,
    research_admission,
    experiment_plan,
    hypothesis_assessment,
    evidence,
    evidence_observation,
    evidence_admission,
    candidate,
    candidate_evidence,
    candidate_admission,
    verification,
    finding_proposal,
    human_review,
    approval,
    finding,
    target_inference,
    differential_observation,
    invariant_hypothesis,
    invariant_source_ref,
    invariant_counterexample_ref,
    chain_hypothesis,
    research_opportunity,
    research_selection,
    snapshot,
    snapshot_member,
    change_event,
    research_orchestration,
    research_cycle,
    budget_consumption,
)

APPEND_ONLY_TABLES = (
    "issued_budget",
    "audit_event",
    "research_reasoning",
    "research_admission",
    "experiment_plan",
    "hypothesis_assessment",
    "evidence",
    "evidence_observation",
    "evidence_admission",
    "candidate_evidence",
    "candidate_admission",
    "verification",
    "human_review",
    "approval",
    "finding",
    "target_inference",
    "differential_observation",
    "invariant_source_ref",
    "invariant_counterexample_ref",
    "chain_hypothesis",
    "research_opportunity",
    "research_selection",
    "snapshot",
    "snapshot_member",
    "change_event",
    "research_cycle",
    "budget_consumption",
)
