"""Core: authorization, policy, scope, budget, and Approval semantics.

Python types here are not language-neutral architectural contracts.
Cross-boundary Worker truth remains `contracts/` JSON Schema.
"""

from research_os.core.approval import ApprovalView, check_approval
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
from research_os.core.enums import (
    ActorType,
    ApprovalDecision,
    AuthorizationSourceState,
    ExecutionDecisionKind,
    ReasonCode,
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

__all__ = [
    "Actor",
    "ActorType",
    "ApprovalDecision",
    "ApprovalView",
    "AuthorizationSourceState",
    "AuthorizationSourceView",
    "BudgetAllocationError",
    "BudgetUsage",
    "CoreInputError",
    "ExecutionDecision",
    "ExecutionDecisionKind",
    "ExecutionRequest",
    "InvalidBudgetError",
    "IssuedBudget",
    "ReasonCode",
    "ScopeDecision",
    "ScopeEvaluationInput",
    "ScopeRuleEffect",
    "ScopeRuleMatch",
    "SideEffectLevel",
    "allocate_experiment_budget",
    "check_approval",
    "check_authorization",
    "check_budget",
    "check_scope",
    "evaluate_execution",
]
