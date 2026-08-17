"""Authenticated CLI/session ModelPort adapter. Codex CLI is an AGENT_RUNTIME.

Documented flags only. Does not scrape credentials. Does not use --yolo.
A diagnostic echo that ignores ModelCallRequest is not MODELPORT_COMPATIBLE.
"""

from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol

from research_os.platform.argv_process import (
    ArgvProcessConfig,
    ArgvProcessResult,
    ArgvProcessStatus,
    resolve_executable,
    run_argv,
)
from research_os.platform.readiness import ReadinessStage, RuntimeReadiness, readiness_from_flags
from research_os.research.model_port import (
    ContentPolicyBlockedError,
    ModelCallRequest,
    ModelCallResult,
    ModelPortError,
    ProviderAuthError,
    ProviderTimeoutError,
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
STRUCTURED_OUTPUT_SCHEMA = {
    "type": "object",
    "additionalProperties": True,
}


class CodexArgvRunner(Protocol):
    def __call__(
        self,
        argv: tuple[str, ...],
        *,
        stdin_bytes: bytes | None = None,
    ) -> ArgvProcessResult: ...


ArgvRunner = Callable[..., ArgvProcessResult]


@dataclass(frozen=True)
class CliRuntimeAvailability:
    available: bool
    outcome: RuntimeOutcome
    executable: str | None
    version: str | None
    detail: str
    readiness: RuntimeReadiness | None = None

    def to_mapping(self) -> dict[str, str | bool | None]:
        payload: dict[str, str | bool | None] = {
            "available": self.available,
            "outcome": self.outcome.value,
            "executable": self.executable,
            "version": self.version,
            "detail": self.detail,
            "unavailable_is_not_pass": True,
        }
        if self.readiness is not None:
            mapping = self.readiness.to_mapping()
            payload["installed"] = mapping["installed"]
            payload["version_known"] = mapping["version_known"]
            payload["auth_ready"] = mapping["auth_ready"]
            payload["modelport_compatible"] = mapping["modelport_compatible"]
            payload["benchmark_compatible"] = mapping["benchmark_compatible"]
            payload["stage"] = mapping["stage"]
        return payload


def _run(
    runner: ArgvRunner | None,
    argv: tuple[str, ...],
    *,
    stdin_bytes: bytes | None = None,
    timeout_ms: int = 5_000,
    working_directory: Path | None = None,
) -> ArgvProcessResult:
    if runner is not None:
        return runner(argv, stdin_bytes=stdin_bytes)
    return run_argv(
        argv,
        config=ArgvProcessConfig(executable=argv[0], working_directory=working_directory),
        stdin_bytes=stdin_bytes,
        timeout_ms=timeout_ms,
    )


def probe_codex_cli(
    *,
    executable_name: str = "codex",
    runner: ArgvRunner | None = None,
) -> CliRuntimeAvailability:
    path = resolve_executable(executable_name)
    if path is None:
        readiness = readiness_from_flags(
            installed=False,
            detail="codex executable not found on PATH",
        )
        return CliRuntimeAvailability(
            available=False,
            outcome=RuntimeOutcome.UNAVAILABLE,
            executable=None,
            version=None,
            detail=readiness.detail,
            readiness=readiness,
        )
    result = _run(runner, (path, "--version"), timeout_ms=5_000)
    if result.status is ArgvProcessStatus.UNAVAILABLE:
        readiness = readiness_from_flags(
            installed=False,
            executable=path,
            detail=result.reason or "codex --version unavailable",
        )
        return CliRuntimeAvailability(
            available=False,
            outcome=RuntimeOutcome.UNAVAILABLE,
            executable=path,
            version=None,
            detail=readiness.detail,
            readiness=readiness,
        )
    if result.status is ArgvProcessStatus.TIMED_OUT:
        readiness = readiness_from_flags(
            installed=True,
            executable=path,
            detail="codex --version timed out",
        )
        return CliRuntimeAvailability(
            available=False,
            outcome=RuntimeOutcome.TIMED_OUT,
            executable=path,
            version=None,
            detail=readiness.detail,
            readiness=readiness,
        )
    if result.status is not ArgvProcessStatus.COMPLETED:
        readiness = readiness_from_flags(
            installed=True,
            executable=path,
            detail=result.stderr.strip() or result.reason or "codex --version failed",
        )
        return CliRuntimeAvailability(
            available=False,
            outcome=RuntimeOutcome.PROCESS_FAILED,
            executable=path,
            version=None,
            detail=readiness.detail,
            readiness=readiness,
        )
    version = (result.stdout or result.stderr).strip().splitlines()[0] if (result.stdout or result.stderr).strip() else "unknown"
    auth = _run(runner, (path, "login", "status"), timeout_ms=5_000)
    auth_ready = auth.status is ArgvProcessStatus.COMPLETED
    auth_detail = "codex login status succeeded" if auth_ready else (
        "codex login status reported unauthenticated"
        if auth.status is ArgvProcessStatus.PROCESS_FAILED
        else (auth.reason or "codex login status not confirmed")
    )
    modelport_compatible = False
    benchmark_compatible = False
    diagnostic_ready = False
    stage_detail = (
        "codex --version succeeded; session material was not copied into Research OS. "
        f"{auth_detail}. MODELPORT_COMPATIBLE requires the request-consuming exec transport "
        "and AUTH_READY."
    )
    if auth_ready:
        diagnostic_ready = True
        modelport_compatible = True
        benchmark_compatible = True
        stage_detail = (
            "codex CLI is authenticated and the request-consuming exec transport is enabled; "
            "tokens were not scraped"
        )
    readiness = readiness_from_flags(
        installed=True,
        version_known=True,
        auth_ready=auth_ready,
        dependencies_ready=auth_ready,
        diagnostic_ready=diagnostic_ready,
        modelport_compatible=modelport_compatible,
        benchmark_compatible=benchmark_compatible,
        detail=stage_detail,
        version=version,
        executable=path,
    )
    return CliRuntimeAvailability(
        available=auth_ready,
        outcome=RuntimeOutcome.COMPLETED if auth_ready else RuntimeOutcome.AUTH_FAILED,
        executable=path,
        version=version,
        detail=readiness.detail,
        readiness=readiness,
    )


class CodexCliSessionAdapter:
    """AGENT_RUNTIME ModelPort over documented Codex CLI exec. Consumes ModelCallRequest."""

    MODELPORT_COMPATIBLE = True

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
        prompt = _prompt_for_request(request)
        with tempfile.TemporaryDirectory(prefix="research-os-codex-") as tmp:
            schema_path = Path(tmp) / "output-schema.json"
            schema_path.write_text(
                json.dumps(STRUCTURED_OUTPUT_SCHEMA, separators=(",", ":")),
                encoding="utf-8",
            )
            cwd = self._working_directory or Path(tmp)
            argv = (
                executable,
                "exec",
                "--sandbox",
                "read-only",
                "--ephemeral",
                "--output-schema",
                str(schema_path),
                "-",
            )
            if any(flag in argv for flag in FORBIDDEN_CLI_FLAGS):
                raise ModelPortError("unrestricted CLI flags are rejected")
            result = _run(
                self._runner,
                argv,
                stdin_bytes=prompt.encode("utf-8"),
                timeout_ms=request.timeout_ms or 15_000,
                working_directory=cwd,
            )
        return _result_from_process(request, result, self._identity, self._version)


class CodexDiagnosticEchoAdapter:
    """Legacy echo probe. Ignores ModelCallRequest. Not MODELPORT_COMPATIBLE."""

    MODELPORT_COMPATIBLE = False

    def __init__(self, *, executable: str | None = None, runner: ArgvRunner | None = None) -> None:
        self._executable = executable
        self._runner = runner

    def complete(self, request: ModelCallRequest) -> ModelCallResult:
        del request
        raise ModelPortError(
            "diagnostic echo adapter ignores ModelCallRequest and is not MODELPORT_COMPATIBLE"
        )


def _prompt_for_request(request: ModelCallRequest) -> str:
    payload = json.dumps(dict(request.payload), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return (
        "SYSTEM:\nYou are a structured-output reasoning runtime. Do not call tools.\n\n"
        f"INSTRUCTIONS:\n{request.instructions}\n\n"
        f"USER:\ncorrelation_id={request.correlation_id}\n"
        f"role={request.role.value}\n"
        f"context_fingerprint={request.context_fingerprint}\n"
        f"payload={payload}\n\n"
        "Reply with a JSON object only."
    )


def _result_from_process(
    request: ModelCallRequest,
    result: ArgvProcessResult,
    identity,
    version: str | None,
) -> ModelCallResult:
    if result.status is ArgvProcessStatus.UNAVAILABLE:
        raise RuntimeUnavailableError(result.reason or "codex CLI unavailable")
    if result.status is ArgvProcessStatus.TIMED_OUT:
        raise ProviderTimeoutError(result.reason or "codex CLI timed out")
    if result.status is ArgvProcessStatus.CANCELLED:
        from research_os.research.model_port import RuntimeCancelledError

        raise RuntimeCancelledError(result.reason or "codex CLI cancelled")
    if result.status is ArgvProcessStatus.PROCESS_FAILED:
        combined = f"{result.stdout} {result.stderr}".lower()
        if "login" in combined or "unauthorized" in combined or "not authenticated" in combined:
            raise ProviderAuthError("codex CLI authentication failed")
        if "policy" in combined or "safety" in combined or "content" in combined:
            raise ContentPolicyBlockedError("codex CLI content/safety policy blocked the request")
        raise RuntimeProcessError(result.reason or "codex CLI process failed")
    raw = result.stdout.strip()
    if not raw:
        raise StructuredOutputTransportError("codex CLI stdout was empty")
    structured = _parse_structured_stdout(raw)
    return ModelCallResult(
        role=request.role,
        adapter_identity=identity.adapter_id,
        provider_adapter_identity="codex-cli",
        structured_output=structured,
        model_id="codex-cli",
        model_version=version,
        runtime_identity=identity,
    )


def _parse_structured_stdout(raw: str) -> dict[str, object]:
    try:
        structured = json.loads(raw)
    except json.JSONDecodeError:
        last_object = None
        for line in raw.splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                last_object = parsed
        if last_object is None:
            raise StructuredOutputTransportError("codex CLI stdout was not structured JSON")
        structured = last_object
    if not isinstance(structured, dict):
        raise StructuredOutputTransportError("codex CLI JSON was not an object")
    return structured
