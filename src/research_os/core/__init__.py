"""Core: authorization, policy, scope, budget, and Approval semantics.

Python types here are not language-neutral architectural contracts.
Cross-boundary Worker truth remains `contracts/` JSON Schema.
"""

from research_os.core.approval import (
    ApprovalView,
    RecordedApprovalEvaluation,
    check_approval,
    evaluate_recorded_approval,
)
from research_os.core.authorization import (
    AuthorizationSourceView,
    check_authorization,
)
from research_os.core.budget import (
    BudgetUsage,
    IssuedBudget,
    allocate_experiment_budget,
    check_budget,
)
from research_os.core.capability import CapabilityAuthorizationView
from research_os.core.enums import (
    ActorType,
    ApprovalDecision,
    AuthorizationSourceState,
    ExecutionDecisionKind,
    ReasonCode,
    ScopeClassification,
    ScopeDecision,
    ScopeRuleEffect,
    SideEffectLevel,
)
from research_os.core.errors import (
    BudgetAllocationError,
    CoreInputError,
    InvalidBudgetError,
)
from research_os.core.execution import ExecutionDecision, ExecutionRequest, evaluate_execution
from research_os.core.identity import Actor
from research_os.core.scope import ScopeEvaluationInput, ScopeRuleMatch, check_scope
from research_os.core.scope_compiler import (
    ScopeCandidate,
    ScopeRuleDefinition,
    compile_scope_rules,
    evaluate_scope_candidate,
)

__all__ = [
    "Actor",
    "ActorType",
    "ApprovalDecision",
    "ApprovalView",
    "RecordedApprovalEvaluation",
    "AuthorizationSourceState",
    "AuthorizationSourceView",
    "BudgetAllocationError",
    "BudgetUsage",
    "CapabilityAuthorizationView",
    "CoreInputError",
    "ExecutionDecision",
    "ExecutionDecisionKind",
    "ExecutionRequest",
    "InvalidBudgetError",
    "IssuedBudget",
    "ReasonCode",
    "ScopeCandidate",
    "ScopeClassification",
    "ScopeDecision",
    "ScopeEvaluationInput",
    "ScopeRuleDefinition",
    "ScopeRuleEffect",
    "ScopeRuleMatch",
    "SideEffectLevel",
    "allocate_experiment_budget",
    "check_approval",
    "evaluate_recorded_approval",
    "check_authorization",
    "check_budget",
    "check_scope",
    "compile_scope_rules",
    "evaluate_execution",
    "evaluate_scope_candidate",
]
