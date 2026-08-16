from __future__ import annotations

import ast
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src" / "research_os"
CORE_DIR = SRC_ROOT / "core"
RESEARCH_DIR = SRC_ROOT / "research"
WORKERS_DIR = REPO_ROOT / "workers"

PERSISTENCE_LIBS = ("sqlalchemy", "psycopg", "alembic")
EXECUTION_ROOTS = (
    "workers",
    "integrations",
    "strix",
    "subprocess",
    "socket",
    "requests",
)
FORBIDDEN_EXACT = {"urllib.request"}


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


def _violations(
    directory: Path,
    *,
    forbidden_roots: tuple[str, ...],
    forbidden_prefixes: tuple[str, ...] = (),
) -> list[str]:
    if not directory.exists():
        return []
    found: list[str] = []
    for path in directory.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for name in _imported_modules(tree):
            if name in FORBIDDEN_EXACT:
                found.append(f"{path.relative_to(REPO_ROOT)} imports {name}")
                continue
            if any(
                name == prefix or name.startswith(prefix + ".")
                for prefix in forbidden_prefixes
            ):
                found.append(f"{path.relative_to(REPO_ROOT)} imports {name}")
                continue
            root = name.split(".", 1)[0]
            if root in forbidden_roots:
                found.append(f"{path.relative_to(REPO_ROOT)} imports {name}")
    return found


class ArchitectureBoundaryTests(unittest.TestCase):
    def test_core_does_not_import_forbidden_namespaces(self) -> None:
        self.assertEqual(
            _violations(
                CORE_DIR,
                forbidden_roots=EXECUTION_ROOTS + PERSISTENCE_LIBS,
                forbidden_prefixes=(
                    "research_os.data",
                    "research_os.workers",
                ),
            ),
            [],
        )

    def test_research_does_not_import_sqlalchemy_or_postgres_adapter(self) -> None:
        self.assertEqual(
            _violations(
                RESEARCH_DIR,
                forbidden_roots=EXECUTION_ROOTS + PERSISTENCE_LIBS,
                forbidden_prefixes=(
                    "research_os.data.postgres",
                    "research_os.workers",
                ),
            ),
            [],
        )

    def test_workers_do_not_import_data_or_postgres(self) -> None:
        self.assertEqual(
            _violations(
                WORKERS_DIR,
                forbidden_roots=PERSISTENCE_LIBS + ("research_os",),
                forbidden_prefixes=("research_os.data",),
            ),
            [],
        )


if __name__ == "__main__":
    unittest.main()
