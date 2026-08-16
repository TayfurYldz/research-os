from __future__ import annotations

from typing import Any


def valid_worker_request(**overrides: Any) -> dict[str, Any]:
    request: dict[str, Any] = {
        "contract_version": "v1",
        "correlation": {
            "correlation_id": "corr-1",
            "research_run_id": "run-1",
            "experiment_id": "exp-1",
            "request_id": "req-1",
        },
        "worker_capability": "diagnostic.echo",
        "action": "echo",
        "target_reference": "target-1",
        "authorization_decision_reference": "authz-1",
        "execution_budget": {
            "budget_id": "budget-1",
            "max_requests": 1,
            "max_tool_calls": 1,
            "max_runtime_ms": 10_000,
            "max_concurrency": 1,
        },
        "side_effect_level": 0,
        "secret_references": [],
        "arguments": {"message": "ping"},
    }
    request.update(overrides)
    return request
