"""Authenticated CLI/session ModelPort adapter. Codex CLI is an AGENT_RUNTIME.

Does not scrape undocumented credentials. Does not use --yolo or unrestricted sandbox.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from research_os.platform.argv_process import (
    ArgvProcessConfig,
    ArgvProcessResult,
    ArgvProcessStatus,
    resolve_executable,
    run_argv,
)
from research_os.research.model_port import (
    ContentPolicyBlockedError,
    ModelCallRequest,
    ModelCallResult,
    ModelPortError,
    RuntimeProcessError,
    RuntimeUnavailableError,
    StructuredOutputTransportError,
)
from research_os.research.model_runtime import (
    RuntimeOutcome,
    cli_session_runtime_identity,
)
from research_os.tools.capabilities import CODEX_DIAGNOSTIC_STRUCTURED_OUTPUT_CAPABILITY

UNRESTRICTED_MARKERS = frozenset({"*", "all", "unrestricted", "shell", "yolo", "danger-full-access"})
FORBIDDEN_CLI_FLAGS = frozenset({"--yolo", "--full-auto", "danger-full-access"})


ArgvRunner = Callable[[tuple[str, ...]], ArgvProcessResult]


@dataclass(frozen=True)
class CliRuntimeAvailability:
    available: bool
    outcome: RuntimeOutcome
    executable: str | None
    version: str | None
    detail: str

    def to_mapping(self) -> dict[str, str | bool | None]:
        return {
            "available": self.available,
            "outcome": self.outcome.value,
            "executable": self.executable,
            "version": self.version,
            "detail": self.detail,
            "unavailable_is_not_pass": True,
        }


def probe_codex_cli(
    *,
    executable_name: str = "codex",
    runner: ArgvRunner | None = None,
) -> CliRuntimeAvailability:
    path = resolve_executable(executable_name)
    if path is None:
        return CliRuntimeAvailability(
            available=False,
            outcome=RuntimeOutcome.UNAVAILABLE,
            executable=None,
            version=None,
            detail="codex executable not found on PATH",
        )
    invoke = runner or (lambda argv: run_argv(argv, timeout_ms=5_000))
    result = invoke((path, "--version"))
    if result.status is ArgvProcessStatus.UNAVAILABLE:
        return CliRuntimeAvailability(
            available=False,
            outcome=RuntimeOutcome.UNAVAILABLE,
            executable=path,
            version=None,
            detail=result.reason or "codex --version unavailable",
        )
    if result.status is ArgvProcessStatus.TIMED_OUT:
        return CliRuntimeAvailability(
            available=False,
            outcome=RuntimeOutcome.TIMED_OUT,
            executable=path,
            version=None,
            detail="codex --version timed out",
        )
    if result.status is not ArgvProcessStatus.COMPLETED:
        return CliRuntimeAvailability(
            available=False,
            outcome=RuntimeOutcome.AUTH_FAILED
            if result.exit_code in {1, 2}
            else RuntimeOutcome.PROCESS_FAILED,
            executable=path,
            version=None,
            detail=result.stderr.strip() or result.reason or "codex --version failed",
        )
    version = (result.stdout or result.stderr).strip().splitlines()[0] if (result.stdout or result.stderr).strip() else "unknown"
    return CliRuntimeAvailability(
        available=True,
        outcome=RuntimeOutcome.COMPLETED,
        executable=path,
        version=version,
        detail="codex --version succeeded; session material was not copied into Research OS",
    )


class CodexCliSessionAdapter:
    """AGENT_RUNTIME ModelPort over documented Codex CLI exec. Not an inference-only API."""

    def __init__(
        self,
        *,
        allowed_capabilities: tuple[str, ...],
        executable: str | None = None,
        version: str | None = None,
        runner: ArgvRunner | None = None,
        working_directory: Path | None = None,
    ) -> None:
        if not allowed_capabilities:
            raise ModelPortError("agent runtime requires an explicit capability set")
        lowered = {item.lower() for item in allowed_capabilities}
        if lowered & UNRESTRICTED_MARKERS:
            raise ModelPortError("unrestricted tool capability is rejected")
        self._allowed = tuple(allowed_capabilities)
        self._executable = executable
        self._version = version
        self._working_directory = working_directory
        if runner is None:
            def _run(argv: tuple[str, ...]) -> ArgvProcessResult:
                return run_argv(
                    argv,
                    config=ArgvProcessConfig(
                        executable=argv[0],
                        working_directory=working_directory,
                    ),
                    timeout_ms=15_000,
                )

            self._runner = _run
        else:
            self._runner = runner
        self._identity = cli_session_runtime_identity(
            adapter_id="codex.cli.session",
            runtime_id="codex-cli",
            runtime_version=version,
            session_reference="local-authenticated-cli-session",
        )

    @property
    def adapter_identity(self) -> str:
        return self._identity.adapter_id

    def complete(self, request: ModelCallRequest) -> ModelCallResult:
        if CODEX_DIAGNOSTIC_STRUCTURED_OUTPUT_CAPABILITY not in self._allowed:
            raise ModelPortError("requested agent capability is not allowlisted")
        executable = self._executable or resolve_executable("codex")
        if executable is None:
            raise RuntimeUnavailableError("codex CLI is UNAVAILABLE")
        argv = (
            executable,
            "exec",
            "--sandbox",
            "read-only",
            "Reply with a JSON object only. Do not call tools. echo=ping.",
        )
        if any(flag in argv for flag in FORBIDDEN_CLI_FLAGS):
            raise ModelPortError("unrestricted CLI flags are rejected")
        result = self._runner(argv)
        if result.status is ArgvProcessStatus.UNAVAILABLE:
            raise RuntimeUnavailableError(result.reason or "codex CLI unavailable")
        if result.status is ArgvProcessStatus.TIMED_OUT:
            from research_os.research.model_port import ProviderTimeoutError

            raise ProviderTimeoutError(result.reason or "codex CLI timed out")
        if result.status is ArgvProcessStatus.PROCESS_FAILED:
            combined = f"{result.stdout} {result.stderr}".lower()
            if "auth" in combined or "login" in combined or "unauthorized" in combined:
                from research_os.research.model_port import ProviderAuthError

                raise ProviderAuthError("codex CLI authentication failed")
            if "policy" in combined or "safety" in combined or "content" in combined:
                raise ContentPolicyBlockedError("codex CLI content/safety policy blocked the request")
            raise RuntimeProcessError(result.reason or "codex CLI process failed")
        raw = result.stdout.strip()
        if not raw:
            raise StructuredOutputTransportError("codex CLI stdout was empty")
        try:
            structured = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise StructuredOutputTransportError("codex CLI stdout was not structured JSON") from exc
        if not isinstance(structured, dict):
            raise StructuredOutputTransportError("codex CLI JSON was not an object")
        return ModelCallResult(
            role=request.role,
            adapter_identity=self._identity.adapter_id,
            provider_adapter_identity="codex-cli",
            structured_output=structured,
            model_id="codex-cli",
            model_version=self._version,
            runtime_identity=self._identity,
        )
