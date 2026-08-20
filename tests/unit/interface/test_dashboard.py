from __future__ import annotations

import unittest

import pathsetup  # noqa: F401

from datetime import datetime, timezone

from research_os.application.identity import new_opaque_id
from research_os.interface.dashboard import (
    HTML,
    _bootstrap_payload,
    _scope_records,
    bootstrap_program,
    collect_dashboard_payload,
)


class DashboardTests(unittest.TestCase):
    def test_collect_payload_degrades_without_database(self) -> None:
        payload = collect_dashboard_payload(
            env={
                "PATH": "",
                "RESEARCH_OS_CODEX_MODELS": "",
            }
        )

        self.assertIn("status", payload)
        self.assertIn("database", payload)
        self.assertEqual(payload["database"]["state"], "UNAVAILABLE")
        self.assertEqual(payload["database"]["programs"], [])
        self.assertEqual(payload["database"]["audit_events"], [])
        rendered = str(payload).lower()
        self.assertNotIn("sk-", rendered)
        self.assertNotIn("password", rendered)
        self.assertNotIn("api_key", rendered)

    def test_html_contains_dashboard_api_and_no_external_assets(self) -> None:
        self.assertIn("/api/dashboard", HTML)
        self.assertNotIn("https://", HTML)
        self.assertNotIn("http://", HTML)
        self.assertIn("Security Operations", HTML)
        self.assertIn("/api/programs/bootstrap", HTML)

    def test_bootstrap_payload_requires_scope(self) -> None:
        with self.assertRaisesRegex(ValueError, "in_scope"):
            _bootstrap_payload(
                {
                    "program_name": "Authorized Test",
                    "target_reference": "local-target",
                    "authorization_reference": "auth-reference",
                    "in_scope": "",
                }
            )

    def test_bootstrap_payload_accepts_yeswehack_platform(self) -> None:
        payload = _bootstrap_payload(
            {
                "program_name": "Authorized Test",
                "platform": "yeswehack",
                "target_reference": "local-target",
                "authorization_reference": "auth-reference",
                "in_scope": "example.test",
            }
        )

        self.assertEqual(payload["platform"], "yeswehack")

    def test_scope_records_parse_exact_and_wildcard_hosts(self) -> None:
        now = datetime.now(timezone.utc)
        records = _scope_records(
            {
                "in_scope": ["https://app.example.test/api", "*.example.test"],
                "out_of_scope": ["admin.example.test"],
            },
            program_id=new_opaque_id(),
            now=now,
        )

        self.assertEqual(len(records), 3)
        self.assertEqual(records[0].host, "app.example.test")
        self.assertEqual(records[0].path_prefix, "/api")
        self.assertEqual(records[1].host_pattern, "*.example.test")
        self.assertEqual(records[2].effect, "OUT_OF_SCOPE")

    def test_bootstrap_program_requires_database_url(self) -> None:
        with self.assertRaisesRegex(ValueError, "RESEARCH_OS_DATABASE_URL"):
            bootstrap_program(
                {
                    "program_name": "Authorized Test",
                    "target_reference": "local-target",
                    "authorization_reference": "auth-reference",
                    "in_scope": "example.test",
                },
                env={},
            )


if __name__ == "__main__":
    unittest.main()
