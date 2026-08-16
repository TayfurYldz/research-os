from __future__ import annotations

import ast
import unittest
from pathlib import Path

CORE_DIR = Path(__file__).resolve().parents[2] / "src" / "research_os" / "core"

FORBIDDEN_ROOTS = (
    "workers",
    "integrations",
    "strix",
    "subprocess",
    "socket",
    "requests",
)
FORBIDDEN_EXACT = {"urllib.request"}
FORBIDDEN_LOCAL_PREFIXES = ("research_os.data", "research_os.workers")


def _imported_modules(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
            if node.module == "urllib":
                for alias in node.names:
                    names.add(f"urllib.{alias.name}")
    return names


class ArchitectureBoundaryTests(unittest.TestCase):
    def test_core_does_not_import_forbidden_namespaces(self) -> None:
        violations: list[str] = []
        for path in CORE_DIR.glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            imported = _imported_modules(tree)
            for name in imported:
                if name in FORBIDDEN_EXACT or any(
                    name == prefix or name.startswith(prefix + ".")
                    for prefix in FORBIDDEN_LOCAL_PREFIXES
                ):
                    violations.append(f"{path.name} imports {name}")
                    continue
                root = name.split(".", 1)[0]
                if root in FORBIDDEN_ROOTS:
                    violations.append(f"{path.name} imports {name}")
        self.assertEqual(violations, [])


if __name__ == "__main__":
    unittest.main()
