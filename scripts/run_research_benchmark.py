"""Run the Research Brain benchmark. Live adapters stay in Integrations."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from research_os.benchmark.runner import identity_for_cli_session, identity_for_live, run_cli
from research_os.interface.git_provenance import collect_source_provenance
from research_os.integrations.models.cli_session import CodexCliSessionAdapter, probe_codex_cli
from research_os.integrations.models.discovery import discover_configured_runtimes, gate_04b_status
from research_os.integrations.models.factory import resolve_live_adapter
from research_os.tools.capabilities import CODEX_DIAGNOSTIC_STRUCTURED_OUTPUT_CAPABILITY


def resolve_live(adapter_id: str, model_id: str | None):
    if adapter_id == "codex-cli":
        availability = probe_codex_cli()
        payload = json.dumps(availability.to_mapping(), ensure_ascii=True)
        if (
            availability.readiness is None
            or not availability.readiness.benchmark_compatible
            or availability.executable is None
        ):
            print(f"UNAVAILABLE {payload}", file=sys.stderr)
            return None
        port = CodexCliSessionAdapter(
            allowed_capabilities=(CODEX_DIAGNOSTIC_STRUCTURED_OUTPUT_CAPABILITY,),
            executable=availability.executable,
            version=availability.version,
        )
        identity = identity_for_cli_session(
            adapter_identity="codex.cli.session",
            runtime_id="codex-cli",
            runtime_version=availability.version,
        )
        return port, identity

    handle = resolve_live_adapter(adapter_id, model_id=model_id)
    payload = json.dumps(handle.availability.to_mapping(), ensure_ascii=True)
    if not handle.availability.available or handle.port is None:
        print(f"UNAVAILABLE {payload}", file=sys.stderr)
        return None
    identity = identity_for_live(
        adapter_identity=handle.adapter_identity or adapter_id,
        provider_adapter_identity=handle.provider_adapter_identity or adapter_id,
        provider_model_id=handle.provider_model_id or (model_id or ""),
    )
    return handle.port, identity


def discover_runtimes():
    return discover_configured_runtimes()


def evaluate_live_status(**kwargs):
    provenance = collect_source_provenance(ROOT)
    kwargs.setdefault("source_authoritative", provenance.authoritative)
    return gate_04b_status(**kwargs)


if __name__ == "__main__":
    provenance = collect_source_provenance(ROOT)
    raise SystemExit(
        run_cli(
            git_commit=provenance.commit_hash,
            resolve_live=resolve_live,
            discover_runtimes=discover_runtimes,
            evaluate_live_status=evaluate_live_status,
        )
    )
