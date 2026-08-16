from __future__ import annotations

import ast
import unittest
from pathlib import Path

import pathsetup  # noqa: F401

from research_os.data.postgres.tables import SPINE_TABLES, metadata

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "src" / "research_os" / "data"
ALEMBIC_ENV = REPO_ROOT / "alembic" / "env.py"
MIGRATION = (
    REPO_ROOT / "alembic" / "versions" / "a3_001_persistence_spine.py"
)


def _imported_modules(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


class AlembicSmokeTests(unittest.TestCase):
    def test_spine_tables_are_exactly_the_a3_set(self) -> None:
        names = {table.name for table in SPINE_TABLES}
        self.assertEqual(
            names,
            {
                "program",
                "authorization_source",
                "research_run",
                "issued_budget",
                "hypothesis",
                "experiment",
                "worker_result",
                "observation",
                "audit_event",
            },
        )
        self.assertEqual(set(metadata.tables), names)

    def test_deferred_domain_tables_are_absent(self) -> None:
        forbidden = {
            "evidence",
            "candidate",
            "verification",
            "finding",
            "finding_proposal",
            "approval",
            "scope_rule",
            "snapshot",
            "change_event",
            "vector",
            "embedding",
        }
        self.assertTrue(forbidden.isdisjoint(metadata.tables))

    def test_data_package_outside_postgres_does_not_import_sqlalchemy(self) -> None:
        violations: list[str] = []
        for path in DATA_DIR.glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for name in _imported_modules(tree):
                root = name.split(".", 1)[0]
                if root in {"sqlalchemy", "psycopg", "alembic"}:
                    violations.append(f"{path.name} imports {name}")
        self.assertEqual(violations, [])

    def test_adapter_does_not_call_create_all(self) -> None:
        for path in [
            *DATA_DIR.rglob("*.py"),
            ALEMBIC_ENV,
        ]:
            source = path.read_text(encoding="utf-8")
            self.assertNotIn(
                "create_all",
                source,
                msg=f"{path} must not use metadata.create_all as startup/schema strategy",
            )

    def test_first_migration_is_the_spine_revision(self) -> None:
        source = MIGRATION.read_text(encoding="utf-8")
        self.assertIn("a3_001_persistence_spine", source)
        self.assertIn("research_os_reject_mutation", source)
        self.assertNotIn("create_all", source)


if __name__ == "__main__":
    unittest.main()
