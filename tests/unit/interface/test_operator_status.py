from __future__ import annotations

import unittest

import pathsetup  # noqa: F401

from research_os.application.operator_status import OperatorStatusSnapshot, render_operator_status
from research_os.interface.cli import build_status_snapshot
from research_os.platform.health import ComponentHealth


class StatusDatabaseSeparationTests(unittest.TestCase):
    def test_application_db_is_not_test_db(self) -> None:
        snapshot = build_status_snapshot(
            env={
                "RESEARCH_OS_DATABASE_URL": "postgresql+psycopg://app:secret-pass@127.0.0.1:5432/research_os",
                "RESEARCH_OS_TEST_DATABASE_URL": "postgresql+psycopg://test:other-pass@127.0.0.1:55432/research_os_test",
            }
        )
        self.assertNotIn("secret-pass", snapshot.application_dsn)
        self.assertNotIn("other-pass", snapshot.test_dsn)
        self.assertIn("research_os_test", snapshot.test_dsn)
        self.assertNotEqual(snapshot.postgresql, snapshot.test_postgresql)
        text = render_operator_status(snapshot)
        self.assertIn("TEST_POSTGRESQL:", text)
        self.assertNotIn("secret-pass", text)
        self.assertNotIn("other-pass", text)

    def test_renderer_keeps_sections(self) -> None:
        text = render_operator_status(
            OperatorStatusSnapshot(
                postgresql=ComponentHealth.HEALTHY.value,
                test_postgresql=ComponentHealth.UNAVAILABLE.value,
                application_dsn="postgresql+psycopg://127.0.0.1/research_os",
                test_dsn="postgresql+psycopg://127.0.0.1/research_os_test",
                worker={"local-python": ComponentHealth.UNAVAILABLE.value},
                model_runtimes={"API": ComponentHealth.UNAVAILABLE.value},
                strix=ComponentHealth.UNAVAILABLE.value,
                auth="runtime-owned sessions only",
                orchestrator="no active run",
                budget_ledger="unknown",
                reconciliation="classifier available",
                observability="structured events",
            )
        )
        self.assertIn("POSTGRESQL:", text)
        self.assertIn("TEST_POSTGRESQL:", text)


if __name__ == "__main__":
    unittest.main()
