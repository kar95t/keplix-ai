"""Unit tests for Keplix AST code engine, diff patcher, locks, and log pruner."""

from pathlib import Path
import tempfile
import unittest

from keplix.engine.locks import SubgraphLockManager
from keplix.engine.log_pruner import LogPruner
from keplix.engine.parser import ASTParser
from keplix.engine.patcher import DiffPatcher

try:
    from keplix.engine.index import DependencyGraph, RepoMapIndexer
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False


class TestEngine(unittest.TestCase):
    def test_ast_symbol_parsing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            file = Path(tmp_dir) / "orbit.py"
            code = """
import os

def calculate_orbit(velocity: float, altitude: float) -> float:
    \"\"\"Compute orbital path.\"\"\"
    return velocity * altitude

class Spacecraft:
    def launch(self):
        return True
"""
            file.write_text(code, encoding="utf-8")

            parser = ASTParser()
            symbols = parser.parse_symbols(file, code)
            imports = parser.parse_imports(file, code)

            self.assertEqual(len(imports), 1)
            self.assertEqual(imports[0].source_module, "os")

            names = {s.name for s in symbols}
            self.assertIn("calculate_orbit", names)
            self.assertIn("Spacecraft", names)

    def test_subgraph_concurrency_locking(self) -> None:
        mgr = SubgraphLockManager()
        token_a = mgr.acquire_lock("worker_1", ["main.py", "utils.py"])
        self.assertIsNotNone(token_a)
        self.assertTrue(mgr.is_locked("main.py"))

        # Worker 2 attempts collision on utils.py
        token_b = mgr.acquire_lock("worker_2", ["utils.py", "config.py"])
        self.assertIsNone(token_b)

        # Worker 1 releases lock
        self.assertTrue(mgr.release_lock(token_a))
        self.assertFalse(mgr.is_locked("main.py"))

        # Worker 2 now succeeds
        token_b = mgr.acquire_lock("worker_2", ["utils.py", "config.py"])
        self.assertIsNotNone(token_b)
        mgr.release_lock(token_b)

    def test_diff_patcher_atomic_replace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            file = Path(tmp_dir) / "greeting.py"
            file.write_text("def hello():\n    return 'world'\n", encoding="utf-8")

            res = DiffPatcher.apply_search_replace(
                file_path=file,
                search_block="return 'world'",
                replace_block="return 'keplix orbit'",
            )
            self.assertTrue(res.success)
            self.assertIn("return 'keplix orbit'", file.read_text(encoding="utf-8"))

            # Non-matching block fails cleanly
            res_fail = DiffPatcher.apply_search_replace(
                file_path=file,
                search_block="non_existent_text",
                replace_block="foo",
            )
            self.assertFalse(res_fail.success)

    def test_log_pruner_redaction(self) -> None:
        pruner = LogPruner()
        raw = "Failed with token Bearer secret_token_value_12345 and sk-abc12345678901234567890"
        cleaned = pruner.redact_secrets(raw)
        self.assertNotIn("secret_token_value_12345", cleaned)
        self.assertIn("[REDACTED_API_KEY]", cleaned)
