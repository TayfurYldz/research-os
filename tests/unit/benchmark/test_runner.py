from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pathsetup  # noqa: F401

from research_os.benchmark.runner import run_cli

REPO = Path(__file__).resolve().parents[3]


class RunnerTests(unittest.TestCase):
    def test_scripted_runner_prints_scorecard_without_magic_score(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report_path = Path(tmp) / "report.json"
            buffer = io.StringIO()
            err = io.StringIO()
            with redirect_stdout(buffer), redirect_stderr(err):
                code = run_cli(
                    [
                        "--baseline",
                        "GOOD_BASELINE",
                        "--scenarios",
                        str(REPO / "benchmarks" / "research" / "scenarios"),
                        "--json-report",
                        str(report_path),
                    ]
                )
            self.assertEqual(code, 0)
            self.assertIn("no aggregate model score", buffer.getvalue())
            payload = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertTrue(payload["no_aggregate_model_score"])
            self.assertTrue(payload["not_evidence"])
            self.assertNotIn("model_score", payload)
            self.assertGreaterEqual(len(payload["scenario_results"]), 10)

    def test_leakage_invariant_returns_nonzero(self) -> None:
        err = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(err):
            code = run_cli(["--baseline", "UNKNOWN_MODEL"])
        self.assertEqual(code, 2)
        self.assertIn("unknown scripted baseline", err.getvalue())


if __name__ == "__main__":
    unittest.main()
