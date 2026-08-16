"""Strix adapter skeleton. Untrusted Integration. Does not write the SoR."""

from __future__ import annotations

from research_os.platform.argv_process import ArgvProcessStatus, resolve_executable, run_argv
from research_os.platform.strix import (
    ALLOWED_STRIX_CAPABILITIES,
    UNRESTRICTED_CAPABILITY_MARKERS,
    StrixExecutionOutcome,
    StrixExecutionRequest,
    StrixRuntimeStatus,
)


def probe_strix_runtime() -> dict[str, object]:
    path = resolve_executable("strix")
    if path is None:
        return {
            "available": False,
            "outcome": "UNAVAILABLE",
            "detail": "strix executable not found on PATH",
            "unavailable_is_not_architecture_failure": True,
        }
    result = run_argv((path, "--version"), timeout_ms=5_000)
    available = result.status is ArgvProcessStatus.COMPLETED
    return {
        "available": available,
        "outcome": "COMPLETED" if available else "UNAVAILABLE",
        "executable": path,
        "detail": (result.stdout or result.stderr or result.reason or "").strip()[:200],
        "unavailable_is_not_architecture_failure": True,
    }


class StrixDiagnosticAdapter:
    """Diagnostic-only StrixIntegration. Security scanning workflows are deferred."""

    def __init__(self, *, executable: str | None = None) -> None:
        self._executable = executable
        self.calls: list[StrixExecutionRequest] = []

    def execute(self, request: StrixExecutionRequest) -> StrixExecutionOutcome:
        self.calls.append(request)
        lowered = {item.lower() for item in request.allowed_capabilities}
        if lowered & UNRESTRICTED_CAPABILITY_MARKERS:
            return StrixExecutionOutcome(
                status=StrixRuntimeStatus.DENIED,
                untrusted=True,
                capability=request.capability,
                reason_codes=("UNRESTRICTED_CAPABILITY_REJECTED",),
                payload={"not_observation": True},
            )
        if request.capability not in request.allowed_capabilities:
            return StrixExecutionOutcome(
                status=StrixRuntimeStatus.DENIED,
                untrusted=True,
                capability=request.capability,
                reason_codes=("CAPABILITY_NOT_ALLOWLISTED",),
                payload={"not_observation": True},
            )
        if request.capability not in ALLOWED_STRIX_CAPABILITIES:
            return StrixExecutionOutcome(
                status=StrixRuntimeStatus.DENIED,
                untrusted=True,
                capability=request.capability,
                reason_codes=("NON_DIAGNOSTIC_STRIX_CAPABILITY_DEFERRED",),
                payload={"not_observation": True},
            )
        executable = self._executable or resolve_executable("strix")
        if executable is None:
            return StrixExecutionOutcome(
                status=StrixRuntimeStatus.UNAVAILABLE,
                untrusted=True,
                capability=request.capability,
                reason_codes=("STRIX_RUNTIME_UNAVAILABLE",),
                payload={"not_observation": True, "not_evidence": True},
            )
        result = run_argv((executable, "--version"), timeout_ms=5_000)
        if result.status is not ArgvProcessStatus.COMPLETED:
            return StrixExecutionOutcome(
                status=StrixRuntimeStatus.PROCESS_FAILED,
                untrusted=True,
                capability=request.capability,
                reason_codes=("STRIX_DIAGNOSTIC_PROCESS_FAILED",),
                payload={"not_observation": True, "not_evidence": True},
            )
        return StrixExecutionOutcome(
            status=StrixRuntimeStatus.COMPLETED,
            untrusted=True,
            capability=request.capability,
            reason_codes=("STRIX_DIAGNOSTIC_PING", "NOT_OBSERVATION", "NOT_EVIDENCE"),
            payload={
                "untrusted": True,
                "echo": "pong",
                "version_text": (result.stdout or "").strip()[:200],
                "not_observation": True,
                "not_evidence": True,
                "not_candidate": True,
                "not_finding": True,
            },
        )
