"""Operator CLI. Composition root. Does not print secrets."""

from __future__ import annotations

import argparse
import os
import sys
from typing import Mapping

from research_os.application.operator_status import OperatorStatusSnapshot, render_operator_status
from research_os.maturity import GATE_04B_STATUS, GATE_14_STATUS, GATE_15_STATUS, SUBSCRIPTION_OAUTH_STATUS
from research_os.platform.health import ComponentHealth


def _health_from_readiness(readiness: str, *, auth_hint: str = "") -> str:
    if readiness == "AVAILABLE":
        return ComponentHealth.HEALTHY.value
    if "auth" in auth_hint.lower() or "credential" in auth_hint.lower() or "unauthenticated" in auth_hint.lower():
        return ComponentHealth.AUTH_REQUIRED.value
    if readiness == "CONFIGURED_NOT_READY":
        return ComponentHealth.DEGRADED.value
    return ComponentHealth.UNAVAILABLE.value


def _probe_application_db(url: str | None) -> tuple[str, str, str]:
    from research_os.data.postgres.engine import create_sync_engine, ping_database, redacted_database_url

    if not url:
        return ComponentHealth.UNAVAILABLE.value, "unset", "no database"
    try:
        dsn = redacted_database_url(url)
    except Exception:
        dsn = "unparseable"
    try:
        engine = create_sync_engine(url)
        ping_database(engine)
        health = ComponentHealth.HEALTHY.value
        orchestrator = "no active run"
        budget = "unknown"
        with engine.connect() as connection:
            from sqlalchemy import text

            row = connection.execute(
                text("SELECT state, COUNT(*) FROM research_orchestration GROUP BY state")
            ).fetchall()
            if row:
                orchestrator = ", ".join(f"{state}={count}" for state, count in row)
            consumed = connection.execute(text("SELECT COUNT(*) FROM budget_consumption")).scalar_one()
            budget = f"append-only rows={consumed}"
        engine.dispose()
        return health, dsn, f"{orchestrator}; {budget}"
    except Exception as exc:
        return ComponentHealth.UNAVAILABLE.value, dsn, f"unavailable ({exc.__class__.__name__})"


def _probe_test_db(url: str | None) -> tuple[str, str]:
    from research_os.data.postgres.engine import create_sync_engine, ping_database, redacted_database_url

    if not url:
        return "not configured", "unset"
    try:
        dsn = redacted_database_url(url)
    except Exception:
        dsn = "unparseable"
    try:
        engine = create_sync_engine(url)
        ping_database(engine)
        engine.dispose()
        return ComponentHealth.HEALTHY.value, dsn
    except Exception as exc:
        return f"{ComponentHealth.UNAVAILABLE.value} ({exc.__class__.__name__})", dsn


def build_status_snapshot(*, env: Mapping[str, str] | None = None, argv_runner=None) -> OperatorStatusSnapshot:
    from research_os.data.postgres.engine import DATABASE_URL_ENV, TEST_DATABASE_URL_ENV
    from research_os.integrations.models.discovery import ProbeMode, discover_configured_runtimes
    from research_os.platform.worker_health import probe_local_python_worker

    source = dict(os.environ if env is None else env)
    postgres, app_dsn, db_detail = _probe_application_db(source.get(DATABASE_URL_ENV))
    test_postgres, test_dsn = _probe_test_db(source.get(TEST_DATABASE_URL_ENV))
    orchestrator = "no database"
    budget = "unknown"
    if postgres == ComponentHealth.HEALTHY.value:
        parts = db_detail.split("; ", 1)
        orchestrator = parts[0]
        budget = parts[1] if len(parts) > 1 else "unknown"
    elif postgres == ComponentHealth.UNAVAILABLE.value:
        orchestrator = "unavailable"
        budget = db_detail

    report = discover_configured_runtimes(
        env=source,
        argv_runner=argv_runner,
        probe_mode=ProbeMode.PASSIVE,
    )
    kind = report.kind_matrix
    model_runtimes = {
        "API": _health_from_readiness(kind.get("API", "UNAVAILABLE")),
        "SUBSCRIPTION_OAUTH": SUBSCRIPTION_OAUTH_STATUS,
        "CLI_SESSION": _health_from_readiness(
            kind.get("CLI_SESSION", "UNAVAILABLE"),
            auth_hint=" ".join(
                item.reason for item in report.entries if item.runtime_kind == "CLI_SESSION"
            ),
        ),
        "LOCAL_MODEL": _health_from_readiness(kind.get("LOCAL_MODEL", "UNAVAILABLE")),
        "EXTERNAL_AGENT": _health_from_readiness(kind.get("EXTERNAL_AGENT", "UNAVAILABLE")),
    }
    strix_entry = next((item for item in report.entries if item.runtime_kind == "STRIX"), None)
    strix = (
        _health_from_readiness(strix_entry.readiness.value)
        if strix_entry is not None
        else ComponentHealth.UNAVAILABLE.value
    )
    worker_check = probe_local_python_worker()
    return OperatorStatusSnapshot(
        postgresql=postgres,
        test_postgresql=test_postgres,
        application_dsn=app_dsn,
        test_dsn=test_dsn,
        worker={"local-python": worker_check.health.value},
        model_runtimes=model_runtimes,
        strix=strix,
        auth="runtime-owned sessions only; tokens are not scraped",
        orchestrator=orchestrator,
        budget_ledger=budget,
        reconciliation="classifier available; no side-effect guessing",
        observability="structured events; not AuditEvent; not Evidence",
        gate_04b=GATE_04B_STATUS,
        gate_14=GATE_14_STATUS,
        gate_15=GATE_15_STATUS,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="research-os")
    parser.add_argument("command", choices=("status", "export-source"))
    args, rest = parser.parse_known_args(argv)
    if args.command == "status":
        sys.stdout.write(render_operator_status(build_status_snapshot()) + "\n")
        return 0
    if args.command == "export-source":
        from research_os.source_export import export_source_archive

        export_parser = argparse.ArgumentParser(prog="research-os export-source")
        export_parser.add_argument("--output", required=True)
        export_parser.add_argument("--include-untracked-source", action="store_true")
        export_args = export_parser.parse_args(rest)
        archive, manifest = export_source_archive(
            export_args.output,
            include_untracked_source=export_args.include_untracked_source,
        )
        sys.stdout.write(f"{archive}\n{manifest}\n")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
