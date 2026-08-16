from __future__ import annotations

import unittest

import pathsetup  # noqa: F401

from research_os.data.postgres.engine import redacted_database_url


class EngineUrlTests(unittest.TestCase):
    def test_password_is_not_rendered(self) -> None:
        url = "postgresql+psycopg://operator:super-secret@localhost:5432/research_os"
        redacted = redacted_database_url(url)
        self.assertNotIn("super-secret", redacted)
        self.assertIn("localhost", redacted)


if __name__ == "__main__":
    unittest.main()
