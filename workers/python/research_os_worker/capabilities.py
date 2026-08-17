"""Deterministic diagnostic capability. Not a security scanner."""

from __future__ import annotations

from typing import Any, Mapping

from research_os_worker.http_authorization import (
    HTTP_AUTHORIZATION_DIFFERENTIAL_ACTION,
    HTTP_AUTHORIZATION_DIFFERENTIAL_CAPABILITY,
    execute_http_authorization,
)

DIAGNOSTIC_ECHO_CAPABILITY = "diagnostic.echo"
DIAGNOSTIC_ECHO_ACTION = "echo"


def execute(request: Mapping[str, Any]) -> tuple[str, dict[str, Any], dict[str, Any] | None]:
    """Return (status, raw_result, diagnostics)."""
    capability = request.get("worker_capability")
    action = request.get("action")
    arguments = request.get("arguments")
    if not isinstance(arguments, Mapping):
        arguments = {}
    if capability == DIAGNOSTIC_ECHO_CAPABILITY and action == DIAGNOSTIC_ECHO_ACTION:
        message = arguments.get("message", "")
        if not isinstance(message, str):
            return (
                "EXECUTION_FAILED",
                {},
                {"error": "diagnostic.echo message must be a string"},
            )
        return (
            "SUCCEEDED",
            {"echoed": message, "capability": DIAGNOSTIC_ECHO_CAPABILITY},
            None,
        )
    if (
        capability == HTTP_AUTHORIZATION_DIFFERENTIAL_CAPABILITY
        and action == HTTP_AUTHORIZATION_DIFFERENTIAL_ACTION
    ):
        return execute_http_authorization(request)
    return (
        "EXECUTION_FAILED",
        {},
        {"error": "unknown diagnostic capability", "capability": capability},
    )
