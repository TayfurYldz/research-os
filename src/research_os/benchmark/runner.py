"""Provider-neutral benchmark runner. No provider SDK. No SoR writes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from research_os.benchmark.baselines import BASELINE_NAMES, create_baseline
from research_os.benchmark.errors import BenchmarkError
from research_os.benchmark.evaluate import evaluate_suite, format_scorecard
from research_os.benchmark.scenarios import load_scenarios
from research_os.research.model_port import ModelPortError

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SCENARIO_DIR = REPO_ROOT / "benchmarks" / "research" / "scenarios"


def scenario_directory(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit)
    cwd = Path.cwd() / "benchmarks" / "research" / "scenarios"
    if cwd.is_dir():
        return cwd
    return DEFAULT_SCENARIO_DIR


def run_cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the Research OS provider-neutral research benchmark. "
            "Does not select a model provider and does not write SoR records."
        )
    )
    parser.add_argument(
        "--baseline",
        default="GOOD_BASELINE",
        help=f"scripted ModelPort identity ({', '.join(BASELINE_NAMES)})",
    )
    parser.add_argument("--scenarios", default=None, help="scenario JSON directory")
    parser.add_argument(
        "--include-holdout",
        action="store_true",
        help="load holdout scenarios (forbidden for prompt/admission tuning)",
    )
    parser.add_argument(
        "--json-report",
        default=None,
        help="optional path for a machine-readable report (not SoR)",
    )
    parser.add_argument(
        "--fail-on-hard-fail",
        action="store_true",
        help="nonzero exit when any hard-fail event is recorded",
    )
    args = parser.parse_args(argv)

    try:
        scenarios = load_scenarios(
            scenario_directory(args.scenarios),
            include_holdout=args.include_holdout,
        )
        model = create_baseline(args.baseline)
        report = evaluate_suite(
            scenarios, model, adapter_identity=model.adapter_identity
        )
    except (BenchmarkError, ModelPortError) as exc:
        print(f"benchmark invariant failure: {exc}", file=sys.stderr)
        return 2

    print(format_scorecard(report))
    if args.json_report:
        path = Path(args.json_report)
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


def main() -> None:
    raise SystemExit(run_cli())
