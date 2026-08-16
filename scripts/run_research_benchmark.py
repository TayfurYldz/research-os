"""Run the Research Brain benchmark. Live adapters stay in Integrations."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from research_os.benchmark.runner import identity_for_live, run_cli


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


def resolve_live(adapter_id: str, model_id: str | None):
    from integrations.models.factory import resolve_live_adapter

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


if __name__ == "__main__":
    raise SystemExit(
        run_cli(git_commit=git_commit_hash(), resolve_live=resolve_live)
    )
