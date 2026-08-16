"""SQLAlchemy Core metadata for the persistence spine. Adapter-only."""

from sqlalchemy import (
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
)

APPEND_ONLY_TABLES = (
    "issued_budget",
    "audit_event",
    "research_reasoning",
    "research_admission",
    "experiment_plan",
    "hypothesis_assessment",
)
