"""Put `src/` on sys.path for stdlib unittest without a package manager."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SRC = str(_ROOT / "src")
_CORE_TESTS = str(Path(__file__).resolve().parent / "core")
_TESTS = str(_ROOT / "tests")
for _path in (_SRC, _CORE_TESTS, _TESTS):
    if _path not in sys.path:
        sys.path.insert(0, _path)
