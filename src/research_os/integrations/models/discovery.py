"""Discover configured model runtimes. Strix is reported separately and is not a ModelRuntime.

Does not scrape credentials. Does not scan localhost. Does not auto-install CLIs.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from os import environ
from typing import Any

from research_os.integrations.models.cli_session import probe_codex_cli
from research_os.integrations.models.external_agent import probe_external_agent
from research_os.integrations.models.factory import LIVE_ADAPTER_IDS, probe_live_adapter
from research_os.integrations.models.local_runtime import probe_local_model
from research_os.integrations.strix.adapter import probe_strix_runtime
from research_os.platform.readiness import RuntimeReadiness
from research_os.research.model_runtime import RuntimeKind


class Readiness(Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    CONFIGURED_NOT_READY = "CONFIGURED_NOT_READY"


LOCAL_ENDPOINT_ENV = "RESEARCH_OS_LOCAL_MODEL_ENDPOINT"
EXTERNAL_AGENT_ENDPOINT_ENV = "RESEARCH_OS_EXTERNAL_AGENT_ENDPOINT"


@dataclass(frozen=True)
class RuntimeDiscoveryEntry:
    runtime_kind: str
    configuration_id: str
    readiness: Readiness
    reason: str
    counts_as_model_runtime: bool
    runtime_version: str | None = None
    runtime_class: str | None = None
    structured_readiness: RuntimeReadiness | None = None

    def to_mapping(self) -> dict[str, Any]:
        payload = {
            "runtime_kind": self.runtime_kind,
            "configuration_id": self.configuration_id,
            "readiness": self.readiness.value,
            "reason": self.reason,
            "counts_as_model_runtime": self.counts_as_model_runtime,
            "runtime_version": self.runtime_version,
            "runtime_class": self.runtime_class,
            "contains_secrets": False,
        }
        if self.structured_readiness is not None:
            payload["structured_readiness"] = self.structured_readiness.to_mapping()
            payload["benchmark_compatible"] = self.structured_readiness.benchmark_compatible
            payload["modelport_compatible"] = self.structured_readiness.modelport_compatible
        return payload


@dataclass(frozen=True)
class RuntimeDiscoveryReport:
    entries: tuple[RuntimeDiscoveryEntry, ...]
    kind_matrix: dict[str, str]
    available_model_configurations: tuple[str, ...]

    def to_mapping(self) -> dict[str, Any]:
        return {
            "entries": [item.to_mapping() for item in self.entries],
            "kind_matrix": dict(self.kind_matrix),
            "available_model_configurations": list(self.available_model_configurations),
            "strix_is_not_model_runtime": True,
            "scripted_does_not_count": True,
            "contains_secrets": False,
        }


def _kind_status(entries: list[RuntimeDiscoveryEntry], kind: str) -> str:
    matching = [item for item in entries if item.runtime_kind == kind]
    if any(item.readiness is Readiness.AVAILABLE for item in matching):
        return Readiness.AVAILABLE.value
    if any(item.readiness is Readiness.CONFIGURED_NOT_READY for item in matching):
        return Readiness.CONFIGURED_NOT_READY.value
    return Readiness.UNAVAILABLE.value


def discover_configured_runtimes(*, env: dict[str, str] | None = None) -> RuntimeDiscoveryReport:
    source = dict(environ if env is None else env)
    entries: list[RuntimeDiscoveryEntry] = []

    for adapter_id in LIVE_ADAPTER_IDS:
        availability = probe_live_adapter(adapter_id, env=source)
        if availability.available:
            readiness = Readiness.AVAILABLE
            reason = "sdk, credential reference, and model id are present"
        elif availability.reason.value in {"MISSING_CREDENTIAL", "MISSING_MODEL_ID"}:
            readiness = Readiness.CONFIGURED_NOT_READY
            reason = availability.detail
        else:
            readiness = Readiness.UNAVAILABLE
            reason = availability.detail
        entries.append(
            RuntimeDiscoveryEntry(
                runtime_kind=RuntimeKind.API.value,
                configuration_id=adapter_id,
                readiness=readiness,
                reason=reason,
                counts_as_model_runtime=True,
                runtime_class="INFERENCE_RUNTIME",
            )
        )

    entries.append(
        RuntimeDiscoveryEntry(
            runtime_kind=RuntimeKind.SUBSCRIPTION_OAUTH.value,
            configuration_id="subscription-oauth",
            readiness=Readiness.UNAVAILABLE,
            reason="no explicit OAuth/subscription adapter is implemented; undocumented tokens are not cloned",
            counts_as_model_runtime=True,
            runtime_class="INFERENCE_RUNTIME",
        )
    )

    cli = probe_codex_cli()
    cli_readiness_struct = cli.readiness
    if cli_readiness_struct is not None and cli_readiness_struct.benchmark_compatible:
        cli_readiness = Readiness.AVAILABLE
        cli_reason = cli.detail
        cli_counts = True
    elif cli.executable is not None:
        cli_readiness = Readiness.CONFIGURED_NOT_READY
        cli_reason = cli.detail
        cli_counts = False
    else:
        cli_readiness = Readiness.UNAVAILABLE
        cli_reason = cli.detail
        cli_counts = False
    entries.append(
        RuntimeDiscoveryEntry(
            runtime_kind=RuntimeKind.CLI_SESSION.value,
            configuration_id="codex-cli",
            readiness=cli_readiness,
            reason=cli_reason,
            counts_as_model_runtime=cli_counts,
            runtime_version=cli.version,
            runtime_class="AGENT_RUNTIME",
            structured_readiness=cli_readiness_struct,
        )
    )

    local_endpoint = source.get(LOCAL_ENDPOINT_ENV)
    local = probe_local_model(endpoint_reference=local_endpoint if local_endpoint else None)
    if local.available:
        local_readiness = Readiness.AVAILABLE
    elif local.endpoint_reference:
        local_readiness = Readiness.CONFIGURED_NOT_READY
    else:
        local_readiness = Readiness.UNAVAILABLE
    entries.append(
        RuntimeDiscoveryEntry(
            runtime_kind=RuntimeKind.LOCAL_MODEL.value,
            configuration_id="local-model",
            readiness=local_readiness,
            reason=local.detail,
            counts_as_model_runtime=True,
            runtime_class="INFERENCE_RUNTIME",
        )
    )

    external_endpoint = source.get(EXTERNAL_AGENT_ENDPOINT_ENV)
    external = probe_external_agent()
    if external_endpoint and not external.available:
        external_readiness = Readiness.CONFIGURED_NOT_READY
        external_reason = "external-agent endpoint is configured but live host transport is deferred"
    else:
        external_readiness = Readiness.UNAVAILABLE
        external_reason = external.detail
    entries.append(
        RuntimeDiscoveryEntry(
            runtime_kind=RuntimeKind.EXTERNAL_AGENT.value,
            configuration_id="external-agent",
            readiness=external_readiness,
            reason=external_reason,
            counts_as_model_runtime=True,
            runtime_class="AGENT_RUNTIME",
        )
    )

    strix = probe_strix_runtime()
    if strix.get("healthy"):
        strix_readiness = Readiness.AVAILABLE
    elif strix.get("installed") or strix.get("executable"):
        strix_readiness = Readiness.CONFIGURED_NOT_READY
    else:
        strix_readiness = Readiness.UNAVAILABLE
    entries.append(
        RuntimeDiscoveryEntry(
            runtime_kind="STRIX",
            configuration_id="strix",
            readiness=strix_readiness,
            reason=str(strix.get("detail") or "strix runtime probe"),
            counts_as_model_runtime=False,
            runtime_class=None,
        )
    )

    kinds = (
        RuntimeKind.API.value,
        RuntimeKind.SUBSCRIPTION_OAUTH.value,
        RuntimeKind.CLI_SESSION.value,
        RuntimeKind.LOCAL_MODEL.value,
        RuntimeKind.EXTERNAL_AGENT.value,
        "STRIX",
    )
    matrix = {kind: _kind_status(entries, kind) for kind in kinds}
    available_models = tuple(
        item.configuration_id
        for item in entries
        if item.counts_as_model_runtime
        and item.readiness is Readiness.AVAILABLE
        and (
            item.structured_readiness is None
            or item.structured_readiness.benchmark_compatible
        )
    )
    return RuntimeDiscoveryReport(
        entries=tuple(entries),
        kind_matrix=matrix,
        available_model_configurations=available_models,
    )


def gate_04b_status(
    *,
    available_model_configurations: tuple[str, ...],
    executed_live_configurations: tuple[str, ...],
    comparable: bool,
    harness_invariant_failed: bool,
    runs_per_scenario: int,
    development_suite: bool,
    source_authoritative: bool = True,
) -> dict[str, Any]:
    """GATE 04B PASS requires >=2 executed comparable live ModelRuntime configurations.

    Availability alone is not PASS. Scripted baselines and Strix do not count.
    """

    if harness_invariant_failed:
        status = "NEEDS_REVIEW"
        reason = "comparison leaked or failed harness invariants"
    elif not source_authoritative:
        status = "PENDING"
        reason = "dirty or untracked source cannot be labelled authoritative GATE 04B"
    elif len(executed_live_configurations) >= 2 and not comparable:
        status = "NEEDS_REVIEW"
        reason = "live runtimes executed but reports are not comparable"
    elif len(executed_live_configurations) >= 2 and runs_per_scenario > 1 and comparable:
        status = "PASS"
        reason = ">=2 real comparable runtime configurations executed"
    else:
        status = "PENDING"
        if len(available_model_configurations) < 2:
            reason = "fewer than 2 live BENCHMARK_COMPATIBLE ModelRuntime configurations are available"
        elif len(executed_live_configurations) < 2:
            reason = "fewer than 2 live configurations were actually executed"
        elif runs_per_scenario <= 1:
            reason = "repeated runs are required for authoritative GATE 04B PASS"
        else:
            reason = "GATE 04B remains PENDING"
    return {
        "status": status,
        "available_model_configurations": list(available_model_configurations),
        "executed_live_configurations": list(executed_live_configurations),
        "comparable": comparable,
        "runs_per_scenario": runs_per_scenario,
        "development_suite": development_suite,
        "source_authoritative": source_authoritative,
        "sealed_holdout_is_unseen_generalization": False,
        "strix_counted_as_model_runtime": False,
        "scripted_counted": False,
        "no_automatic_winner": True,
        "reason": reason,
    }
