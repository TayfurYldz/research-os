from __future__ import annotations

import unittest

import pathsetup  # noqa: F401

from research_os.interface.dashboard import HTML, collect_dashboard_payload


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


if __name__ == "__main__":
    unittest.main()
