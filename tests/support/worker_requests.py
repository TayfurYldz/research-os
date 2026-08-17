from __future__ import annotations

from typing import Any

from research_os.tools.registry import load_capability_registry


def valid_worker_request(**overrides: Any) -> dict[str, Any]:
    capability = str(overrides.get("worker_capability") or "diagnostic.echo")
    action = str(overrides.get("action") or "echo")
    version = "1"
    fingerprint = "unbound-test-fingerprint"
    found = load_capability_registry().lookup(capability, action)
    if found is not None:
        definition, _action = found
        version = definition.version
        fingerprint = definition.definition_fingerprint
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
        "capability_version": version,
        "capability_definition_fingerprint": fingerprint,
        "secret_references": [],
        "arguments": {"message": "ping"},
    }
    request.update(overrides)
    if "capability_version" not in overrides or "capability_definition_fingerprint" not in overrides:
        capability = str(request["worker_capability"])
        action = str(request["action"])
        found = load_capability_registry().lookup(capability, action)
        if found is not None:
            definition, _action = found
            if "capability_version" not in overrides:
                request["capability_version"] = definition.version
            if "capability_definition_fingerprint" not in overrides:
                request["capability_definition_fingerprint"] = definition.definition_fingerprint
    return request
