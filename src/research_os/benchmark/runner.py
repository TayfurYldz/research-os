"""Provider-neutral benchmark runner. No provider SDK. No SoR writes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from research_os.benchmark.baselines import BASELINE_NAMES, create_baseline
from research_os.benchmark.errors import BenchmarkError
from research_os.benchmark.evaluate import evaluate_suite, format_scorecard
from research_os.benchmark.experiment import (
    compare_experiments,
    format_experiment_scorecard,
    format_paired,
    run_experiment,
    write_immutable_report,
)
from research_os.benchmark.holdout import HOLDOUT_PATH_ENV, load_sealed_holdout, resolve_holdout_path
from research_os.benchmark.identity import (
    DEFAULT_RUNS_PER_SCENARIO,
    DEFAULT_SUITE_ID,
    BenchmarkExperimentConfig,
    ModelConfigurationIdentity,
)
from research_os.benchmark.scenarios import load_scenarios
from research_os.research.cycle import (
    FALSIFIER_INSTRUCTION_VERSION,
    GENERATOR_INSTRUCTION_VERSION,
    STRUCTURED_OUTPUT_SPEC_VERSION,
)
from research_os.research.model_port import ModelPortError

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SCENARIO_DIR = REPO_ROOT / "benchmarks" / "research" / "scenarios"
DEFAULT_RESULTS_DIR = REPO_ROOT / "var" / "benchmark-results"


def scenario_directory(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit)
    cwd = Path.cwd() / "benchmarks" / "research" / "scenarios"
    if cwd.is_dir():
        return cwd
    return DEFAULT_SCENARIO_DIR


def identity_for_scripted(name: str) -> ModelConfigurationIdentity:
    return ModelConfigurationIdentity(
        adapter_identity=name,
        provider_adapter_identity=name,
        generator_configuration=name,
        falsifier_configuration=name,
    )


def identity_for_live(
    *,
    adapter_identity: str,
    provider_adapter_identity: str,
    provider_model_id: str,
) -> ModelConfigurationIdentity:
    return ModelConfigurationIdentity(
        adapter_identity=adapter_identity,
        provider_adapter_identity=provider_adapter_identity,
        provider_model_id=provider_model_id,
        generator_configuration=GENERATOR_INSTRUCTION_VERSION,
        falsifier_configuration=FALSIFIER_INSTRUCTION_VERSION,
        reasoning_settings=STRUCTURED_OUTPUT_SPEC_VERSION,
    )


LIVE_ADAPTER_IDS = frozenset({"openai", "anthropic", "gemini"})


def resolve_scripted_adapter(adapter_id: str, model_id: str | None = None):
    del model_id
    if adapter_id not in BASELINE_NAMES:
        return None
    model = create_baseline(adapter_id)
    return model, identity_for_scripted(adapter_id)


def run_cli(
    argv: list[str] | None = None,
    *,
    git_commit: str = "unknown",
    resolve_live=None,
) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the Research OS provider-neutral research benchmark. "
            "Does not select a model provider and does not write SoR records. "
            "Single-run results are not an authoritative real-model comparison."
        )
    )
    parser.add_argument(
        "--baseline",
        default="GOOD_BASELINE",
        help=f"scripted ModelPort identity ({', '.join(BASELINE_NAMES)})",
    )
    parser.add_argument(
        "--compare-baseline",
        default=None,
        help="optional second scripted baseline for paired comparison (no automatic winner)",
    )
    parser.add_argument("--scenarios", default=None, help="development scenario JSON directory")
    parser.add_argument(
        "--include-calibration",
        action="store_true",
        help="also load calibration scenarios (not sealed holdout)",
    )
    parser.add_argument(
        "--include-holdout",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--sealed-holdout-path",
        default=None,
        help=f"external sealed holdout directory (or {HOLDOUT_PATH_ENV})",
    )
    parser.add_argument(
        "--runs-per-scenario",
        type=int,
        default=DEFAULT_RUNS_PER_SCENARIO,
        help="repeated runs per scenario (default 3; 1 is not an authoritative real-model comparison)",
    )
    parser.add_argument(
        "--json-report",
        default=None,
        help="optional explicit JSON path (refuses overwrite)",
    )
    parser.add_argument(
        "--write-results",
        action="store_true",
        help="write an immutable JSON artifact under var/benchmark-results/",
    )
    parser.add_argument(
        "--fail-on-hard-fail",
        action="store_true",
        help="nonzero exit when any hard-fail event is recorded",
    )
    parser.add_argument(
        "--single-run-legacy",
        action="store_true",
        help="GATE 04A one-pass scorecard (not an authoritative real-model comparison)",
    )
    parser.add_argument(
        "--adapter",
        default=None,
        help="scripted baseline name or live adapter id (openai, anthropic, gemini)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="provider model id for a live adapter; required when the adapter is live",
    )
    parser.add_argument(
        "--compare-adapter",
        default=None,
        help="optional second adapter for paired comparison (no automatic winner)",
    )
    parser.add_argument(
        "--compare-model",
        default=None,
        help="provider model id for --compare-adapter when that adapter is live",
    )
    args = parser.parse_args(argv)

    if args.include_holdout:
        print(
            "in-repo --include-holdout is not a sealed holdout; "
            f"use --sealed-holdout-path or {HOLDOUT_PATH_ENV}",
            file=sys.stderr,
        )
        return 2

    try:
        scenarios = load_scenarios(
            scenario_directory(args.scenarios),
            include_calibration=args.include_calibration,
        )
        holdout = load_sealed_holdout(resolve_holdout_path(args.sealed_holdout_path))
        if args.sealed_holdout_path and not holdout.available:
            print(f"sealed holdout unavailable: {holdout.reason}", file=sys.stderr)
            return 2
        if args.single_run_legacy:
            model = create_baseline(args.baseline)
            report = evaluate_suite(
                scenarios, model, adapter_identity=model.adapter_identity
            )
            print(format_scorecard(report))
            if args.json_report:
                path = Path(args.json_report)
                if path.exists():
                    raise BenchmarkError(f"refusing to overwrite benchmark report: {path}")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    json.dumps(report.to_mapping(), indent=2, ensure_ascii=True) + "\n",
                    encoding="utf-8",
                )
                print(f"json report: {path}")
            if report.harness_invariant_failed:
                return 2
            if args.fail_on_hard_fail and report.hard_fail_event_count() > 0:
                return 1
            return 0

        config = BenchmarkExperimentConfig(
            suite_id=DEFAULT_SUITE_ID,
            runs_per_scenario=args.runs_per_scenario,
            include_calibration=args.include_calibration,
        )
        git_commit = git_commit.strip() or "unknown"
        left_name = args.adapter or args.baseline
        left_loaded = _load_configured_adapter(
            left_name, args.model, resolve_live=resolve_live
        )
        if left_loaded is None:
            print(
                f"adapter {left_name!r} UNAVAILABLE (not a benchmark failure)",
                file=sys.stderr,
            )
            return 0
        if isinstance(left_loaded, str):
            print(left_loaded, file=sys.stderr)
            return 0
        left_model, left_identity = left_loaded
        left_report = run_experiment(
            scenarios,
            left_model,
            config=config,
            model_identity=left_identity,
            git_commit=git_commit,
            holdout=holdout,
        )
        print(format_experiment_scorecard(left_report))
        right_name = args.compare_adapter or args.compare_baseline
        if right_name:
            right_loaded = _load_configured_adapter(
                right_name, args.compare_model, resolve_live=resolve_live
            )
            if right_loaded is None or isinstance(right_loaded, str):
                print(
                    "compare adapter UNAVAILABLE; paired comparison PENDING "
                    "(not a fake PASS)",
                    file=sys.stderr,
                )
                if isinstance(right_loaded, str):
                    print(right_loaded, file=sys.stderr)
            else:
                right_model, right_identity = right_loaded
                right_report = run_experiment(
                    scenarios,
                    right_model,
                    config=config,
                    model_identity=right_identity,
                    git_commit=git_commit,
                    holdout=holdout,
                )
                print()
                print(format_experiment_scorecard(right_report))
                print()
                print(format_paired(compare_experiments(left_report, right_report)))
        if args.write_results:
            written = write_immutable_report(DEFAULT_RESULTS_DIR, left_report)
            print(f"immutable report: {written}")
        if args.json_report:
            path = Path(args.json_report)
            if path.exists():
                raise BenchmarkError(f"refusing to overwrite benchmark report: {path}")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(left_report.to_mapping(), indent=2, ensure_ascii=True) + "\n",
                encoding="utf-8",
            )
            print(f"json report: {path}")
    except (BenchmarkError, ModelPortError) as exc:
        print(f"benchmark invariant failure: {exc}", file=sys.stderr)
        return 2

    if left_report.harness_invariant_failed:
        return 2
    if args.fail_on_hard_fail:
        events = sum(
            1
            for summary in left_report.summaries
            for run in summary.runs
            for _code in run.hard_failures
        )
        if events:
            return 1
    return 0


def _load_configured_adapter(
    adapter_id: str,
    model_id: str | None,
    *,
    resolve_live,
):
    scripted = resolve_scripted_adapter(adapter_id, model_id)
    if scripted is not None:
        return scripted
    if adapter_id in LIVE_ADAPTER_IDS:
        if resolve_live is None:
            return (
                f"adapter {adapter_id!r} UNAVAILABLE: live adapters are resolved by "
                "scripts/run_research_benchmark.py (not a benchmark failure)"
            )
        return resolve_live(adapter_id, model_id)
    raise BenchmarkError(f"unknown scripted baseline: {adapter_id}")


def main() -> None:
    raise SystemExit(run_cli())
