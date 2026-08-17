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
A11_MIGRATION = ALEMBIC_VERSIONS / "a11_001_candidate_verification.py"
A12_MIGRATION = ALEMBIC_VERSIONS / "a12_001_finding_acceptance.py"
A13_MIGRATION = ALEMBIC_VERSIONS / "a13_001_target_differential.py"
A14_MIGRATION = ALEMBIC_VERSIONS / "a14_001_invariant_chain.py"
A15_MIGRATION = ALEMBIC_VERSIONS / "a15_001_exploration_temporal.py"
A16_MIGRATION = ALEMBIC_VERSIONS / "a16_001_orchestration_operations.py"
A17_MIGRATION = ALEMBIC_VERSIONS / "a17_001_qa_remediation.py"


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
                "candidate",
                "candidate_evidence",
                "candidate_admission",
                "verification",
                "finding_proposal",
                "human_review",
                "approval",
                "finding",
                "target_inference",
                "differential_observation",
                "invariant_hypothesis",
                "invariant_source_ref",
                "invariant_counterexample_ref",
                "chain_hypothesis",
                "research_opportunity",
                "research_selection",
                "snapshot",
                "snapshot_member",
                "change_event",
                "research_orchestration",
                "research_cycle",
                "budget_consumption",
            },
        )
        self.assertEqual(set(metadata.tables), names)

    def test_deferred_domain_tables_are_absent(self) -> None:
        forbidden = {
            "scope_rule",
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

    def test_a11_migration_is_append_only_revision(self) -> None:
        source = A11_MIGRATION.read_text(encoding="utf-8")
        self.assertIn("a11_001_candidate_verification", source)
        self.assertIn("a10_001_evidence_admission", source)
        self.assertIn("candidate_admission", source)
        self.assertIn("verification", source)
        self.assertNotIn("create_all", source)
        a10 = A10_MIGRATION.read_text(encoding="utf-8")
        self.assertNotIn("CREATE TABLE candidate", a10)
        a3 = MIGRATION.read_text(encoding="utf-8")
        self.assertNotIn("CREATE TABLE candidate", a3)

    def test_a12_migration_is_append_only_revision(self) -> None:
        source = A12_MIGRATION.read_text(encoding="utf-8")
        self.assertIn("a12_001_finding_acceptance", source)
        self.assertIn("a11_001_candidate_verification", source)
        self.assertIn("finding_proposal", source)
        self.assertIn("human_review", source)
        self.assertIn("approval", source)
        self.assertIn("finding", source)
        self.assertNotIn("create_all", source)
        a11 = A11_MIGRATION.read_text(encoding="utf-8")
        self.assertNotIn("CREATE TABLE finding", a11)
        a3 = MIGRATION.read_text(encoding="utf-8")
        self.assertNotIn("CREATE TABLE finding", a3)

    def test_a13_migration_is_append_only_revision(self) -> None:
        source = A13_MIGRATION.read_text(encoding="utf-8")
        self.assertIn("a13_001_target_differential", source)
        self.assertIn("a12_001_finding_acceptance", source)
        self.assertIn("target_inference", source)
        self.assertIn("differential_observation", source)
        self.assertNotIn("create_all", source)
        a12 = A12_MIGRATION.read_text(encoding="utf-8")
        self.assertNotIn("CREATE TABLE target_inference", a12)
        a3 = MIGRATION.read_text(encoding="utf-8")
        self.assertNotIn("CREATE TABLE target_inference", a3)

    def test_a14_migration_is_append_only_revision(self) -> None:
        source = A14_MIGRATION.read_text(encoding="utf-8")
        self.assertIn("a14_001_invariant_chain", source)
        self.assertIn("a13_001_target_differential", source)
        self.assertIn("invariant_hypothesis", source)
        self.assertIn("chain_hypothesis", source)
        self.assertNotIn("create_all", source)
        a13 = A13_MIGRATION.read_text(encoding="utf-8")
        self.assertNotIn("CREATE TABLE invariant_hypothesis", a13)
        self.assertNotIn("CREATE TABLE chain_hypothesis", a13)
        a3 = MIGRATION.read_text(encoding="utf-8")
        self.assertNotIn("CREATE TABLE invariant_hypothesis", a3)

    def test_a15_migration_is_append_only_revision(self) -> None:
        source = A15_MIGRATION.read_text(encoding="utf-8")
        self.assertIn("a15_001_exploration_temporal", source)
        self.assertIn("a14_001_invariant_chain", source)
        self.assertIn("research_opportunity", source)
        self.assertIn("research_selection", source)
        self.assertIn("snapshot", source)
        self.assertIn("change_event", source)
        self.assertNotIn("create_all", source)
        a14 = A14_MIGRATION.read_text(encoding="utf-8")
        self.assertNotIn("CREATE TABLE research_opportunity", a14)
        self.assertNotIn("CREATE TABLE snapshot", a14)
        self.assertNotIn("CREATE TABLE change_event", a14)
        a3 = MIGRATION.read_text(encoding="utf-8")
        self.assertNotIn("CREATE TABLE research_opportunity", a3)
        self.assertNotIn("CREATE TABLE snapshot", a3)

    def test_a16_migration_is_append_only_revision(self) -> None:
        source = A16_MIGRATION.read_text(encoding="utf-8")
        self.assertIn("a16_001_orchestration_operations", source)
        self.assertIn("a15_001_exploration_temporal", source)
        self.assertIn("research_orchestration", source)
        self.assertIn("research_cycle", source)
        self.assertIn("budget_consumption", source)
        self.assertNotIn("create_all", source)
        a15 = A15_MIGRATION.read_text(encoding="utf-8")
        self.assertNotIn("CREATE TABLE research_orchestration", a15)
        self.assertNotIn("CREATE TABLE budget_consumption", a15)
        a3 = MIGRATION.read_text(encoding="utf-8")
        self.assertNotIn("CREATE TABLE research_orchestration", a3)
        self.assertNotIn("CREATE TABLE budget_consumption", a3)

    def test_a17_migration_does_not_edit_a16(self) -> None:
        source = A17_MIGRATION.read_text(encoding="utf-8")
        self.assertIn("a17_001_qa_remediation", source)
        self.assertIn("a16_001_orchestration_operations", source)
        self.assertIn("configuration_fingerprint", source)
        self.assertIn("current_phase", source)
        self.assertNotIn("create_all", source)
        a16 = A16_MIGRATION.read_text(encoding="utf-8")
        self.assertNotIn("configuration_fingerprint", a16)


if __name__ == "__main__":
    unittest.main()
