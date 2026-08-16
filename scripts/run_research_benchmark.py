"""Run the provider-neutral Research Brain benchmark. No provider SDK required."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from research_os.benchmark.runner import run_cli


def git_commit_hash() -> str:
    """Engineering metadata only. Not Domain. Unknown if git is unavailable."""
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(ROOT),
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return "unknown"
    if completed.returncode != 0:
        return "unknown"
    return completed.stdout.strip() or "unknown"


if __name__ == "__main__":
    raise SystemExit(run_cli(git_commit=git_commit_hash()))
