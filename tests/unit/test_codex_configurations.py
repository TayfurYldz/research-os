from __future__ import annotations

import json
import unittest

import pathsetup  # noqa: F401

from research_os.integrations.models.cli_session import (
    CODEX_MODELS_ENV,
    CodexCliConfigurationError,
    CodexCliSessionAdapter,
    derive_codex_configuration_id,
    load_codex_model_configurations,
    parse_codex_model_configurations,
    probe_codex_cli,
    probe_codex_configurations,
)
from research_os.integrations.models.discovery import (
    Readiness,
    discover_configured_runtimes,
    gate_04b_status,
)
from research_os.platform.argv_process import ArgvProcessResult, ArgvProcessStatus
from research_os.platform.readiness import ReadinessStage
from research_os.research.model_port import ModelCallRequest, ModelRole
from research_os.research.model_runtime import cli_session_runtime_identity
from research_os.tools.capabilities import CODEX_DIAGNOSTIC_STRUCTURED_OUTPUT_CAPABILITY


def _request() -> ModelCallRequest:
    return ModelCallRequest(
        role=ModelRole.GENERATOR,
        correlation_id="c1",
        context_fingerprint="fp",
        instructions="propose",
        payload={"note": "ok"},
    )


def _argv_runner(allowed_models: frozenset[str]):
    def runner(argv, stdin_bytes=None):
        del stdin_bytes
        if argv[-1] == "--version":
            return ArgvProcessResult(
                status=ArgvProcessStatus.COMPLETED,
                argv=argv,
                exit_code=0,
                stdout="codex 0.0.0",
            )
        if len(argv) >= 2 and argv[1] == "login":
            return ArgvProcessResult(
                status=ArgvProcessStatus.COMPLETED,
                argv=argv,
                exit_code=0,
                stdout="logged in",
            )
        if "danger-full-access" in argv or "--yolo" in argv:
            return ArgvProcessResult(
                status=ArgvProcessStatus.PROCESS_FAILED,
                argv=argv,
                exit_code=1,
                stderr="forbidden flag",
            )
        model = None
        if "-m" in argv:
            model = argv[argv.index("-m") + 1]
        if model in allowed_models:
            return ArgvProcessResult(
                status=ArgvProcessStatus.COMPLETED,
                argv=argv,
                exit_code=0,
                stdout='{"diagnostic": true}',
            )
        return ArgvProcessResult(
            status=ArgvProcessStatus.PROCESS_FAILED,
            argv=argv,
            exit_code=1,
            stderr=f"unknown model {model}",
        )

    return runner


class CodexConfigurationParseTests(unittest.TestCase):
    def test_defaults_are_operational_not_architecture(self) -> None:
        configs = parse_codex_model_configurations(None)
        self.assertEqual(
            [(item.configuration_id, item.model) for item in configs],
            [("codex-cli-terra", "gpt-5.6-terra"), ("codex-cli-gpt55", "gpt-5.5")],
        )
        for item in configs:
            self.assertEqual(item.runtime_kind, "CLI_SESSION")
            self.assertEqual(item.runtime_class, "AGENT_RUNTIME")
            self.assertTrue(item.ephemeral)
            self.assertEqual(item.sandbox, "read-only")

    def test_model_override_and_derived_ids(self) -> None:
        configs = parse_codex_model_configurations("gpt-5.6-terra,gpt-5.5")
        self.assertEqual(configs[0].configuration_id, derive_codex_configuration_id("gpt-5.6-terra"))
        self.assertEqual(configs[1].configuration_id, derive_codex_configuration_id("gpt-5.5"))
        self.assertEqual(configs[0].model, "gpt-5.6-terra")
        self.assertEqual(configs[1].model, "gpt-5.5")

    def test_explicit_ids(self) -> None:
        configs = load_codex_model_configurations(
            {CODEX_MODELS_ENV: "codex-cli-terra=gpt-5.6-terra,codex-cli-gpt55=gpt-5.5"}
        )
        self.assertEqual(configs[0].configuration_id, "codex-cli-terra")
        self.assertEqual(configs[1].configuration_id, "codex-cli-gpt55")

    def test_duplicate_configuration_fails_closed(self) -> None:
        with self.assertRaises(CodexCliConfigurationError):
            parse_codex_model_configurations("gpt-5.5,gpt-5.5")
        with self.assertRaises(CodexCliConfigurationError):
            parse_codex_model_configurations("alpha=gpt-5.5,alpha=gpt-5.4")

    def test_empty_entries_fail_closed(self) -> None:
        with self.assertRaises(CodexCliConfigurationError):
            parse_codex_model_configurations("gpt-5.5,")
        with self.assertRaises(CodexCliConfigurationError):
            parse_codex_model_configurations(" ,gpt-5.5")
        with self.assertRaises(CodexCliConfigurationError):
            parse_codex_model_configurations("codex-cli-terra=")


class CodexIndependentReadinessTests(unittest.TestCase):
    def test_two_valid_models_are_independently_benchmark_compatible(self) -> None:
        env = {
            CODEX_MODELS_ENV: "codex-cli-terra=gpt-5.6-terra,codex-cli-gpt55=gpt-5.5",
            "RESEARCH_OS_CODEX_EXECUTABLE": "codex",
        }
        runner = _argv_runner(frozenset({"gpt-5.6-terra", "gpt-5.5"}))
        results = probe_codex_configurations(env=env, runner=runner)
        self.assertEqual(len(results), 2)
        for item in results:
            assert item.readiness is not None
            self.assertTrue(item.readiness.installed)
            self.assertTrue(item.readiness.version_known)
            self.assertTrue(item.readiness.auth_ready)
            self.assertTrue(item.readiness.diagnostic_ready)
            self.assertTrue(item.readiness.modelport_compatible)
            self.assertTrue(item.readiness.benchmark_compatible)
            self.assertEqual(item.readiness.stage, ReadinessStage.BENCHMARK_COMPATIBLE)
            self.assertTrue(item.available)
        self.assertNotEqual(results[0].configuration_fingerprint, results[1].configuration_fingerprint)

    def test_one_valid_one_unavailable_does_not_infer_compatibility(self) -> None:
        env = {
            CODEX_MODELS_ENV: "codex-cli-terra=gpt-5.6-terra,codex-cli-gpt55=gpt-5.5",
            "RESEARCH_OS_CODEX_EXECUTABLE": "codex",
        }
        results = probe_codex_configurations(
            env=env,
            runner=_argv_runner(frozenset({"gpt-5.6-terra"})),
        )
        by_id = {item.configuration_id: item for item in results}
        terra = by_id["codex-cli-terra"]
        gpt55 = by_id["codex-cli-gpt55"]
        assert terra.readiness is not None
        assert gpt55.readiness is not None
        self.assertTrue(terra.readiness.benchmark_compatible)
        self.assertFalse(gpt55.readiness.benchmark_compatible)
        self.assertTrue(gpt55.readiness.auth_ready)
        self.assertFalse(gpt55.available)

    def test_exec_argv_is_documented_and_model_specific(self) -> None:
        captured = {}

        def runner(argv, stdin_bytes=None):
            captured["argv"] = argv
            captured["stdin"] = stdin_bytes
            return ArgvProcessResult(
                status=ArgvProcessStatus.COMPLETED,
                argv=argv,
                exit_code=0,
                stdout='{"ok": true}',
            )

        adapter = CodexCliSessionAdapter(
            allowed_capabilities=(CODEX_DIAGNOSTIC_STRUCTURED_OUTPUT_CAPABILITY,),
            executable="codex",
            model="gpt-5.5",
            configuration_id="codex-cli-gpt55",
            runner=runner,
        )
        adapter.complete(_request())
        argv = captured["argv"]
        self.assertEqual(argv[1], "exec")
        self.assertIn("--ignore-user-config", argv)
        self.assertIn("--ephemeral", argv)
        self.assertEqual(argv[argv.index("--sandbox") + 1], "read-only")
        self.assertEqual(argv[argv.index("-m") + 1], "gpt-5.5")
        self.assertNotIn("--yolo", argv)
        self.assertNotIn("danger-full-access", argv)
        self.assertNotIn("dangerously-bypass-approvals-and-sandbox", argv)
        self.assertIn(b"propose", captured["stdin"] or b"")

    def test_independent_fingerprints_include_model(self) -> None:
        first = cli_session_runtime_identity(
            adapter_id="codex.cli.session",
            runtime_id="codex-cli-terra",
            model_id="gpt-5.6-terra",
            runtime_configuration={"sandbox": "read-only", "ephemeral": True, "executable": "codex"},
        )
        second = cli_session_runtime_identity(
            adapter_id="codex.cli.session",
            runtime_id="codex-cli-gpt55",
            model_id="gpt-5.5",
            runtime_configuration={"sandbox": "read-only", "ephemeral": True, "executable": "codex"},
        )
        self.assertNotEqual(first.configuration_fingerprint, second.configuration_fingerprint)
        self.assertEqual(first.runtime_kind.value, "CLI_SESSION")
        serialized = json.dumps(first.to_mapping())
        self.assertNotIn("sk-", serialized)
        self.assertNotIn("token=", serialized)

    def test_no_credential_leakage_in_probe_payload(self) -> None:
        env = {
            CODEX_MODELS_ENV: "codex-cli-terra=gpt-5.6-terra",
            "RESEARCH_OS_CODEX_EXECUTABLE": "codex",
            "OPENAI_API_KEY": "sk-secret-value",
        }
        result = probe_codex_cli(
            configuration=parse_codex_model_configurations(
                env[CODEX_MODELS_ENV], executable="codex"
            )[0],
            runner=_argv_runner(frozenset({"gpt-5.6-terra"})),
        )
        serialized = json.dumps(result.to_mapping())
        self.assertNotIn("sk-secret-value", serialized)
        self.assertNotIn("sk-", serialized)

    def test_host_probe_without_model_is_not_benchmark_compatible(self) -> None:
        availability = probe_codex_cli(runner=_argv_runner(frozenset({"gpt-5.5"})))
        assert availability.readiness is not None
        self.assertTrue(availability.readiness.auth_ready)
        self.assertFalse(availability.readiness.benchmark_compatible)
        self.assertFalse(availability.readiness.diagnostic_ready)


class CodexDiscoveryTests(unittest.TestCase):
    def test_available_model_configurations_requires_independent_readiness(self) -> None:
        env = {
            CODEX_MODELS_ENV: "codex-cli-terra=gpt-5.6-terra,codex-cli-gpt55=gpt-5.5",
            "RESEARCH_OS_CODEX_EXECUTABLE": "codex",
        }
        both = discover_configured_runtimes(
            env=env,
            argv_runner=_argv_runner(frozenset({"gpt-5.6-terra", "gpt-5.5"})),
        )
        self.assertEqual(
            both.available_model_configurations,
            ("codex-cli-terra", "codex-cli-gpt55"),
        )
        strix = next(item for item in both.entries if item.runtime_kind == "STRIX")
        self.assertFalse(strix.counts_as_model_runtime)
        mixed = discover_configured_runtimes(
            env=env,
            argv_runner=_argv_runner(frozenset({"gpt-5.6-terra"})),
        )
        self.assertEqual(mixed.available_model_configurations, ("codex-cli-terra",))
        pending = gate_04b_status(
            available_model_configurations=both.available_model_configurations,
            executed_live_configurations=(),
            comparable=False,
            harness_invariant_failed=False,
            runs_per_scenario=3,
            development_suite=True,
        )
        self.assertEqual(pending["status"], "PENDING")
        self.assertFalse(pending["strix_counted_as_model_runtime"])
        serialized = json.dumps(both.to_mapping())
        self.assertNotIn("sk-", serialized)
        terra = next(item for item in both.entries if item.configuration_id == "codex-cli-terra")
        gpt55 = next(item for item in both.entries if item.configuration_id == "codex-cli-gpt55")
        self.assertEqual(terra.readiness, Readiness.AVAILABLE)
        self.assertEqual(gpt55.readiness, Readiness.AVAILABLE)
        self.assertNotEqual(terra.configuration_fingerprint, gpt55.configuration_fingerprint)

    def test_invalid_configuration_is_not_available(self) -> None:
        report = discover_configured_runtimes(
            env={CODEX_MODELS_ENV: "gpt-5.5,gpt-5.5", "RESEARCH_OS_CODEX_EXECUTABLE": "codex"}
        )
        self.assertNotIn("gpt-5.5", report.available_model_configurations)
        cli = [item for item in report.entries if item.runtime_kind == "CLI_SESSION"]
        self.assertTrue(cli)
        self.assertTrue(all(item.readiness is not Readiness.AVAILABLE for item in cli))


if __name__ == "__main__":
    unittest.main()
