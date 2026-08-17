from __future__ import annotations

import ast
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src" / "research_os"
CORE_DIR = SRC_ROOT / "core"
RESEARCH_DIR = SRC_ROOT / "research"
APPLICATION_DIR = SRC_ROOT / "application"
BENCHMARK_DIR = SRC_ROOT / "benchmark"
PLATFORM_DIR = SRC_ROOT / "platform"
WORKERS_DIR = REPO_ROOT / "workers"

PERSISTENCE_LIBS = ("sqlalchemy", "psycopg", "alembic")
SCHEMA_LIBS = ("jsonschema", "referencing")
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
                forbidden_roots=EXECUTION_ROOTS + PERSISTENCE_LIBS + SCHEMA_LIBS,
                forbidden_prefixes=(
                    "research_os.data",
                    "research_os.workers",
                    "research_os.platform.local_process_worker",
                    "research_os.application",
                    "research_os.research",
                    "research_os.benchmark",
                    "research_os.integrations",
                ),
            ),
            [],
        )

    def test_research_does_not_import_sqlalchemy_or_postgres_adapter(self) -> None:
        self.assertEqual(
            _violations(
                RESEARCH_DIR,
                forbidden_roots=EXECUTION_ROOTS
                + PERSISTENCE_LIBS
                + SCHEMA_LIBS
                + (
                    "openai",
                    "anthropic",
                    "google",
                    "langchain",
                    "llama_index",
                    "litellm",
                    "neo4j",
                    "networkx",
                    "chromadb",
                    "faiss",
                    "pinecone",
                ),
                forbidden_prefixes=(
                    "research_os.data",
                    "research_os.workers",
                    "research_os.platform",
                    "research_os.application",
                    "research_os.benchmark",
                    "research_os.integrations",
                    "google.generativeai",
                    "google.genai",
                ),
            ),
            [],
        )

    def test_application_does_not_import_concrete_adapters(self) -> None:
        self.assertEqual(
            _violations(
                APPLICATION_DIR,
                forbidden_roots=EXECUTION_ROOTS
                + PERSISTENCE_LIBS
                + ("openai", "anthropic", "google", "langchain"),
                forbidden_prefixes=(
                    "research_os.data.postgres",
                    "research_os.platform.local_process_worker",
                    "research_os.workers",
                    "research_os.benchmark",
                    "integrations",
                    "research_os.integrations",
                    "google.generativeai",
                    "google.genai",
                ),
            ),
            [],
        )

    def test_benchmark_does_not_import_sor_providers_or_workers(self) -> None:
        self.assertEqual(
            _violations(
                BENCHMARK_DIR,
                forbidden_roots=EXECUTION_ROOTS
                + PERSISTENCE_LIBS
                + SCHEMA_LIBS
                + ("openai", "anthropic", "google", "langchain", "llama_index", "litellm"),
                forbidden_prefixes=(
                    "research_os.data",
                    "research_os.application",
                    "research_os.workers",
                    "research_os.platform",
                    "research_os.integrations",
                    "google.generativeai",
                    "google.genai",
                ),
            ),
            [],
        )

    def test_platform_does_not_import_application_or_research(self) -> None:
        self.assertEqual(
            _violations(
                PLATFORM_DIR,
                forbidden_roots=(),
                forbidden_prefixes=("research_os.application", "research_os.research"),
            ),
            [],
        )

    def test_workers_do_not_import_application(self) -> None:
        self.assertEqual(
            _violations(
                WORKERS_DIR,
                forbidden_roots=PERSISTENCE_LIBS + SCHEMA_LIBS + ("research_os",),
                forbidden_prefixes=("research_os.data", "research_os.application"),
            ),
            [],
        )
        self.assertEqual(
            _violations(
                SRC_ROOT / "worker_runtime",
                forbidden_roots=PERSISTENCE_LIBS + SCHEMA_LIBS,
                forbidden_prefixes=(
                    "research_os.data",
                    "research_os.application",
                    "research_os.core",
                    "research_os.research",
                    "research_os.integrations",
                ),
            ),
            [],
        )

    def test_local_process_adapter_does_not_use_shell_or_data(self) -> None:
        path = SRC_ROOT / "platform" / "local_process_worker.py"
        text = path.read_text(encoding="utf-8")
        self.assertIn("shell=False", text)
        self.assertNotIn("shell=True", text)
        tree = ast.parse(text, filename=str(path))
        found = []
        for name in _imported_modules(tree):
            root = name.split(".", 1)[0]
            if root in PERSISTENCE_LIBS or name.startswith("research_os.data") or name.startswith(
                "research_os.core"
            ) or name.startswith("research_os.research"):
                found.append(name)
        self.assertEqual(found, [])

    def test_platform_ports_do_not_import_subprocess(self) -> None:
        port_files = [
            SRC_ROOT / "platform" / "worker.py",
            SRC_ROOT / "platform" / "contract_validation.py",
            SRC_ROOT / "platform" / "strix.py",
            SRC_ROOT / "platform" / "__init__.py",
        ]
        found = []
        for path in port_files:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for name in _imported_modules(tree):
                if name.split(".", 1)[0] == "subprocess":
                    found.append(f"{path.name} imports {name}")
        self.assertEqual(found, [])

    def test_argv_process_adapter_does_not_use_shell_or_domain(self) -> None:
        path = SRC_ROOT / "platform" / "argv_process.py"
        text = path.read_text(encoding="utf-8")
        self.assertIn("shell=False", text)
        self.assertNotRegex(text, r"shell\s*=\s*True")
        self.assertNotIn("argv_process", (SRC_ROOT / "platform" / "__init__.py").read_text(encoding="utf-8"))
        tree = ast.parse(text, filename=str(path))
        found = []
        for name in _imported_modules(tree):
            if name.startswith("research_os.data") or name.startswith("research_os.core") or name.startswith(
                "research_os.research"
            ):
                found.append(name)
        self.assertEqual(found, [])

    def test_strix_adapter_does_not_import_data_or_core(self) -> None:
        path = SRC_ROOT / "integrations" / "strix" / "adapter.py"
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        found = []
        for name in _imported_modules(tree):
            if name.startswith("research_os.data") or name.startswith("research_os.core"):
                found.append(name)
        self.assertEqual(found, [])

    def test_agent_runtime_adapters_do_not_import_core(self) -> None:
        paths = [
            SRC_ROOT / "integrations" / "models" / "cli_session.py",
            SRC_ROOT / "integrations" / "models" / "external_agent.py",
        ]
        found = []
        for path in paths:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for name in _imported_modules(tree):
                if name.startswith("research_os.core") or name.startswith("research_os.data"):
                    found.append(f"{path.name} imports {name}")
        self.assertEqual(found, [])


if __name__ == "__main__":
    unittest.main()
