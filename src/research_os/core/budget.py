"""Immutable Core-issued budget eligibility. No persistent decrement."""

from dataclasses import dataclass

from research_os.core.enums import ReasonCode
from research_os.core.errors import (
    BudgetAllocationError,
    CoreInputError,
    InvalidBudgetError,
)
from research_os.core.identity import require_opaque_id


def _require_non_negative(name: str, value: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise InvalidBudgetError(f"{name} must be a non-negative int; 0 is not unlimited")


@dataclass(frozen=True)
class IssuedBudget:
    """ResearchRun envelope or an Experiment allocation inside that envelope."""

    budget_id: str
    max_requests: int
    max_tool_calls: int
    max_runtime_ms: int
    max_concurrency: int

    def __post_init__(self) -> None:
        require_opaque_id(self.budget_id, "budget_id")
        _require_non_negative("max_requests", self.max_requests)
        _require_non_negative("max_tool_calls", self.max_tool_calls)
        _require_non_negative("max_runtime_ms", self.max_runtime_ms)
        _require_non_negative("max_concurrency", self.max_concurrency)


@dataclass(frozen=True)
class BudgetUsage:
    requests: int
    tool_calls: int
    runtime_ms: int
    concurrency: int

    def __post_init__(self) -> None:
        _require_non_negative("requests", self.requests)
        _require_non_negative("tool_calls", self.tool_calls)
        _require_non_negative("runtime_ms", self.runtime_ms)
        _require_non_negative("concurrency", self.concurrency)


@dataclass(frozen=True)
class BudgetCheck:
    allowed_to_continue: bool
    reason_code: ReasonCode
    budget_id: str


def allocate_experiment_budget(
    parent: IssuedBudget,
    budget_id: str,
    max_requests: int,
    max_tool_calls: int,
    max_runtime_ms: int,
    max_concurrency: int,
) -> IssuedBudget:
    child = IssuedBudget(
        budget_id=budget_id,
        max_requests=max_requests,
        max_tool_calls=max_tool_calls,
        max_runtime_ms=max_runtime_ms,
        max_concurrency=max_concurrency,
    )
    if (
        child.max_requests > parent.max_requests
        or child.max_tool_calls > parent.max_tool_calls
        or child.max_runtime_ms > parent.max_runtime_ms
        or child.max_concurrency > parent.max_concurrency
    ):
        raise BudgetAllocationError(
            "Experiment allocation cannot exceed the parent ResearchRun envelope"
        )
    return child


def check_budget(
    issued: IssuedBudget,
    usage: BudgetUsage,
    requested_budget_id: str,
) -> BudgetCheck:
    if not isinstance(issued, IssuedBudget):
        raise CoreInputError("issued_budget is required")
    if not isinstance(usage, BudgetUsage):
        raise CoreInputError("budget_usage is required")
    require_opaque_id(requested_budget_id, "requested_budget_id")
    if requested_budget_id != issued.budget_id:
        return BudgetCheck(False, ReasonCode.BUDGET_MISMATCH, issued.budget_id)
    exhausted = (
        usage.requests >= issued.max_requests
        or usage.tool_calls >= issued.max_tool_calls
        or usage.runtime_ms >= issued.max_runtime_ms
        or usage.concurrency >= issued.max_concurrency
    )
    if exhausted:
        return BudgetCheck(False, ReasonCode.BUDGET_EXHAUSTED, issued.budget_id)
    return BudgetCheck(True, ReasonCode.ALLOWED, issued.budget_id)
