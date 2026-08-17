from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pathsetup  # noqa: F401

from research_os.platform.contract_validation import ContractValidator
from research_os.platform.package_resources import contract_schema_documents, iter_packaged_scenario_json
from research_os.source_export import export_source_archive, find_source_root


class PackagedResourceTests(unittest.TestCase):
    def test_contract_validator_uses_packaged_schemas(self) -> None:
        validator = ContractValidator()
        schemas = contract_schema_documents()
        self.assertIn("urn:research-os:contracts:v1:worker-request", schemas)
        self.assertGreaterEqual(len(schemas), 2)

    def test_development_scenarios_are_packaged(self) -> None:
        names = [name for name, _ in iter_packaged_scenario_json()]
        self.assertTrue(any(name.endswith(".json") for name in names))
        self.assertFalse(any("holdout" in name.lower() and "sealed" in name.lower() for name in names))

    def test_source_export_excludes_git_and_venv(self) -> None:
        root = find_source_root()
        with tempfile.TemporaryDirectory() as tmp:
            archive, manifest = export_source_archive(Path(tmp) / "source.tar.gz", root=root)
            text = manifest.read_text(encoding="utf-8")
            self.assertNotIn("  .git/", text)
            self.assertNotIn("  .venv/", text)
            self.assertTrue(archive.is_file())
            self.assertIn("src/research_os/", text)


if __name__ == "__main__":
    unittest.main()
