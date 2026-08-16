from __future__ import annotations

import ast
import unittest
from pathlib import Path

import pathsetup  # noqa: F401

from research_os.data.postgres.tables import SPINE_TABLES, metadata

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "src" / "research_os" / "data"
ALEMBIC_ENV = REPO_ROOT / "alembic" / "env.py"
ALEMBIC_VERSIONS = REPO_ROOT / "alembic" / "versions"
MIGRATION = ALEMBIC_VERSIONS / "a3_001_persistence_spine.py"
A6_MIGRATION = ALEMBIC_VERSIONS / "a6_001_transition_a_provenance.py"
A7_MIGRATION = ALEMBIC_VERSIONS / "a7_001_execution_attempt.py"
A8_MIGRATION = ALEMBIC_VERSIONS / "a8_001_research_reasoning.py"
A9_MIGRATION = ALEMBIC_VERSIONS / "a9_001_learning_cycle.py"
A10_MIGRATION = ALEMBIC_VERSIONS / "a10_001_evidence_admission.py"


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
                "execution_attempt",
                "worker_result",
                "observation",
                "audit_event",
                "research_reasoning",
                "research_admission",
                "experiment_plan",
                "hypothesis_assessment",
                "evidence",
                "evidence_observation",
                "evidence_admission",
            },
        )
        self.assertEqual(set(metadata.tables), names)

    def test_deferred_domain_tables_are_absent(self) -> None:
        forbidden = {
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

    def test_a6_migration_is_append_only_revision(self) -> None:
        source = A6_MIGRATION.read_text(encoding="utf-8")
        self.assertIn("a6_001_transition_a_provenance", source)
        self.assertIn("a3_001_persistence_spine", source)
        self.assertIn("uq_worker_result_request_id", source)
        self.assertNotIn("create_all", source)
        a3 = MIGRATION.read_text(encoding="utf-8")
        self.assertNotIn("uq_worker_result_request_id", a3)

    def test_a7_migration_is_append_only_revision(self) -> None:
        source = A7_MIGRATION.read_text(encoding="utf-8")
        self.assertIn("a7_001_execution_attempt", source)
        self.assertIn("a6_001_transition_a_provenance", source)
        self.assertIn("uq_execution_attempt_request_id", source)
        self.assertNotIn("create_all", source)
        a6 = A6_MIGRATION.read_text(encoding="utf-8")
        self.assertNotIn("execution_attempt", a6)
        a3 = MIGRATION.read_text(encoding="utf-8")
        self.assertNotIn("execution_attempt", a3)

    def test_a8_migration_is_append_only_revision(self) -> None:
        source = A8_MIGRATION.read_text(encoding="utf-8")
        self.assertIn("a8_001_research_reasoning", source)
        self.assertIn("a7_001_execution_attempt", source)
        self.assertIn("research_reasoning", source)
        self.assertNotIn("create_all", source)
        a7 = A7_MIGRATION.read_text(encoding="utf-8")
        self.assertNotIn("research_reasoning", a7)

    def test_a9_migration_is_append_only_revision(self) -> None:
        source = A9_MIGRATION.read_text(encoding="utf-8")
        self.assertIn("a9_001_learning_cycle", source)
        self.assertIn("a8_001_research_reasoning", source)
        self.assertIn("research_admission", source)
        self.assertIn("experiment_plan", source)
        self.assertIn("hypothesis_assessment", source)
        self.assertNotIn("create_all", source)
        a8 = A8_MIGRATION.read_text(encoding="utf-8")
        self.assertNotIn("research_admission", a8)
        self.assertNotIn("hypothesis_assessment", a8)

    def test_a10_migration_is_append_only_revision(self) -> None:
        source = A10_MIGRATION.read_text(encoding="utf-8")
        self.assertIn("a10_001_evidence_admission", source)
        self.assertIn("a9_001_learning_cycle", source)
        self.assertIn("evidence_admission", source)
        self.assertNotIn("create_all", source)
        a9 = A9_MIGRATION.read_text(encoding="utf-8")
        self.assertNotIn("evidence_admission", a9)
        a3 = MIGRATION.read_text(encoding="utf-8")
        self.assertNotIn("CREATE TABLE evidence", a3)


if __name__ == "__main__":
    unittest.main()
