"""Argv process runner for CLI/session runtimes. First transport, not architecture.

Does not import Research. Does not copy database URLs or provider API keys.
shell=False always.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import threading
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

DEFAULT_MAX_STDOUT_BYTES = 1_048_576
DEFAULT_MAX_STDERR_BYTES = 65_536
DEFAULT_TIMEOUT_MS = 15_000
FORBIDDEN_CHILD_ENV_MARKERS = (
    "SECRET",
    "PASSWORD",
    "TOKEN",
    "API_KEY",
    "DATABASE_URL",
    "POSTGRES",
    "OPENAI",
    "ANTHROPIC",
    "AWS_",
    "RESEARCH_OS_",
)
FORBIDDEN_CHILD_ENV_EXACT = {
    "RESEARCH_OS_DATABASE_URL",
    "RESEARCH_OS_TEST_DATABASE_URL",
}
PASSTHROUGH_ENV = (
    "PATH",
    "PATHEXT",
    "SYSTEMROOT",
    "WINDIR",
    "TEMP",
    "TMP",
    "HOME",
    "USERPROFILE",
    "HOMEDRIVE",
    "HOMEPATH",
    "LANG",
    "LC_ALL",
    "COMSPEC",
)


class ArgvProcessStatus(Enum):
    COMPLETED = "COMPLETED"
    UNAVAILABLE = "UNAVAILABLE"
    TIMED_OUT = "TIMED_OUT"
    PROCESS_FAILED = "PROCESS_FAILED"
    PROTOCOL_ERROR = "PROTOCOL_ERROR"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class ArgvProcessResult:
    status: ArgvProcessStatus
    argv: tuple[str, ...]
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    stderr_truncated: bool = False
    reason: str | None = None


@dataclass(frozen=True)
class ArgvProcessConfig:
    executable: str
    extra_argv: tuple[str, ...] = ()
    working_directory: Path | None = None
    timeout_ms: int = DEFAULT_TIMEOUT_MS
    max_stdout_bytes: int = DEFAULT_MAX_STDOUT_BYTES
    max_stderr_bytes: int = DEFAULT_MAX_STDERR_BYTES
    extra_env: tuple[tuple[str, str], ...] = ()


def build_cli_environment(extra_env: tuple[tuple[str, str], ...] = ()) -> dict[str, str]:
    env: dict[str, str] = {}
    for key in PASSTHROUGH_ENV:
        value = os.environ.get(key)
        if value:
            env[key] = value
    for key, value in extra_env:
        env[key] = value
    for key in list(env):
        upper = key.upper()
        if key in FORBIDDEN_CHILD_ENV_EXACT or any(
            marker in upper for marker in FORBIDDEN_CHILD_ENV_MARKERS
        ):
            del env[key]
    return env


def resolve_executable(name: str) -> str | None:
    return shutil.which(name)


def _decode(data: bytes) -> str:
    return data.decode("utf-8", errors="replace")


def _read_stream(stream, max_bytes: int, *, truncate: bool, collected: dict[str, object]) -> None:
    buf = bytearray()
    exceeded = False
    while True:
        chunk = stream.read(4096)
        if not chunk:
            break
        if len(buf) + len(chunk) > max_bytes:
            exceeded = True
            if truncate:
                remain = max_bytes - len(buf)
                if remain > 0:
                    buf.extend(chunk[:remain])
            while True:
                extra = stream.read(65536)
                if not extra:
                    break
            break
        buf.extend(chunk)
    collected["data"] = bytes(buf)
    collected["exceeded"] = exceeded


def run_argv(
    argv: tuple[str, ...],
    *,
    config: ArgvProcessConfig | None = None,
    stdin_bytes: bytes | None = None,
    timeout_ms: int | None = None,
) -> ArgvProcessResult:
    """Run one argv vector. Never uses a shell."""

    if not argv or not argv[0].strip():
        return ArgvProcessResult(
            status=ArgvProcessStatus.UNAVAILABLE,
            argv=argv,
            reason="executable is empty",
        )
    cfg = config or ArgvProcessConfig(executable=argv[0])
    timeout = timeout_ms if timeout_ms is not None else cfg.timeout_ms
    env = build_cli_environment(cfg.extra_env)
    cwd = str(cfg.working_directory) if cfg.working_directory is not None else None
    try:
        process = subprocess.Popen(
            list(argv),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            shell=False,
            cwd=cwd,
        )
    except FileNotFoundError:
        return ArgvProcessResult(
            status=ArgvProcessStatus.UNAVAILABLE,
            argv=argv,
            reason="executable not found",
        )
    except OSError as exc:
        return ArgvProcessResult(
            status=ArgvProcessStatus.PROCESS_FAILED,
            argv=argv,
            reason=str(exc),
        )

    stdout_box: dict[str, object] = {}
    stderr_box: dict[str, object] = {}
    assert process.stdout is not None
    assert process.stderr is not None
    stdout_thread = threading.Thread(
        target=_read_stream,
        args=(process.stdout, cfg.max_stdout_bytes),
        kwargs={"truncate": False, "collected": stdout_box},
        daemon=True,
    )
    stderr_thread = threading.Thread(
        target=_read_stream,
        args=(process.stderr, cfg.max_stderr_bytes),
        kwargs={"truncate": True, "collected": stderr_box},
        daemon=True,
    )
    stdout_thread.start()
    stderr_thread.start()
    try:
        if stdin_bytes is not None and process.stdin is not None:
            try:
                process.stdin.write(stdin_bytes)
            except OSError:
                pass
        if process.stdin is not None:
            process.stdin.close()
        try:
            exit_code = process.wait(timeout=timeout / 1000.0)
        except subprocess.TimeoutExpired:
            process.kill()
            try:
                process.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                pass
            stdout_thread.join(timeout=1.0)
            stderr_thread.join(timeout=1.0)
            return ArgvProcessResult(
                status=ArgvProcessStatus.TIMED_OUT,
                argv=argv,
                exit_code=process.returncode,
                stdout=_decode(stdout_box.get("data", b"") or b""),
                stderr=_decode(stderr_box.get("data", b"") or b""),
                stderr_truncated=bool(stderr_box.get("exceeded")),
                reason="process exceeded timeout",
            )
        stdout_thread.join(timeout=1.0)
        stderr_thread.join(timeout=1.0)
    finally:
        for pipe in (process.stdin, process.stdout, process.stderr):
            if pipe is not None:
                try:
                    pipe.close()
                except OSError:
                    pass
    stdout_text = _decode(stdout_box.get("data", b"") or b"")
    stderr_text = _decode(stderr_box.get("data", b"") or b"")
    if stdout_box.get("exceeded"):
        return ArgvProcessResult(
            status=ArgvProcessStatus.PROTOCOL_ERROR,
            argv=argv,
            exit_code=exit_code,
            stdout="",
            stderr=stderr_text,
            stderr_truncated=bool(stderr_box.get("exceeded")),
            reason="stdout exceeded max_stdout_bytes",
        )
    if exit_code != 0:
        return ArgvProcessResult(
            status=ArgvProcessStatus.PROCESS_FAILED,
            argv=argv,
            exit_code=exit_code,
            stdout=stdout_text,
            stderr=stderr_text,
            stderr_truncated=bool(stderr_box.get("exceeded")),
            reason="non-zero exit",
        )
    return ArgvProcessResult(
        status=ArgvProcessStatus.COMPLETED,
        argv=argv,
        exit_code=exit_code,
        stdout=stdout_text,
        stderr=stderr_text,
        stderr_truncated=bool(stderr_box.get("exceeded")),
    )
