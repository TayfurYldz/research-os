"""Budget-enforced ModelPort decorator.

Reserves MODEL_CALL on the append-only ledger BEFORE the external invocation.
Does not hold a PostgreSQL transaction open across the model call.

A reserved attempt that crashes before the network still consumes one allowance.
Replay of the same invocation identity does not double-charge.
"""

from __future__ import annotations

from research_os.application.budget_consumption import RecordBudgetConsumption, RecordBudgetConsumptionCommand
from research_os.application.ports import Clock, SystemClock, UnitOfWorkFactory
from research_os.research.model_port import ModelCallRequest, ModelCallResult, ModelPort, ModelRole


def model_invocation_request_id(*, cycle_id: str, role: ModelRole, attempt_no: int) -> str:
    return f"cycle:{cycle_id}:{role.value.lower()}:{attempt_no}"


class BudgetEnforcedModelPort:
    """Application decorator. Research ModelPort remains provider-neutral."""

    def __init__(
        self,
        inner: ModelPort,
        uow_factory: UnitOfWorkFactory,
        *,
        budget_id: str,
        research_run_id: str,
        cycle_id: str,
        clock: Clock | None = None,
    ) -> None:
        self._inner = inner
        self._consume = RecordBudgetConsumption(uow_factory, clock=clock or SystemClock())
        self._budget_id = budget_id
        self._research_run_id = research_run_id
        self._cycle_id = cycle_id
        self._attempts = {ModelRole.GENERATOR: 0, ModelRole.FALSIFIER: 0}
        self.reserved_invocations: list[str] = []

    def complete(self, request: ModelCallRequest) -> ModelCallResult:
        self._attempts[request.role] = self._attempts.get(request.role, 0) + 1
        invocation_id = model_invocation_request_id(
            cycle_id=self._cycle_id,
            role=request.role,
            attempt_no=self._attempts[request.role],
        )
        self._consume.execute(
            RecordBudgetConsumptionCommand(
                budget_id=self._budget_id,
                research_run_id=self._research_run_id,
                resource_type="MODEL_CALL",
                amount=1,
                unit="count",
                provenance="budget_enforced_model_port.complete",
                request_id=invocation_id,
            )
        )
        self.reserved_invocations.append(invocation_id)
        return self._inner.complete(request)
