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


def run_cli(argv: list[str] | None = None, *, git_commit: str = "unknown") -> int:
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
        left_model = create_baseline(args.baseline)
        left_identity = ModelConfigurationIdentity(
            adapter_identity=left_model.adapter_identity,
            provider_adapter_identity=left_model.adapter_identity,
            generator_configuration=args.baseline,
            falsifier_configuration=args.baseline,
        )
        left_report = run_experiment(
            scenarios,
            left_model,
            config=config,
            model_identity=left_identity,
            git_commit=git_commit,
            holdout=holdout,
        )
        print(format_experiment_scorecard(left_report))
        if args.compare_baseline:
            right_model = create_baseline(args.compare_baseline)
            right_identity = ModelConfigurationIdentity(
                adapter_identity=right_model.adapter_identity,
                provider_adapter_identity=right_model.adapter_identity,
                generator_configuration=args.compare_baseline,
                falsifier_configuration=args.compare_baseline,
            )
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


def main() -> None:
    raise SystemExit(run_cli())
