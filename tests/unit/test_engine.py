"""Unit tests for Keplix AST code engine, diff patcher, locks, and log pruner."""

from pathlib import Path

from keplix.engine.index import DependencyGraph, RepoMapIndexer
from keplix.engine.locks import SubgraphLockManager
from keplix.engine.log_pruner import LogPruner
from keplix.engine.parser import ASTParser
from keplix.engine.patcher import DiffPatcher


def test_ast_symbol_parsing(tmp_path: Path) -> None:
    code = """
import os

def calculate_orbit(velocity: float, altitude: float) -> float:
    \"\"\"Compute orbital path.\"\"\"
    return velocity * altitude

class Spacecraft:
    def launch(self):
        return True
"""
    file = tmp_path / "orbit.py"
    file.write_text(code, encoding="utf-8")

    parser = ASTParser()
    symbols = parser.parse_symbols(file, code)
    imports = parser.parse_imports(file, code)

    assert len(imports) == 1
    assert imports[0].source_module == "os"

    names = {s.name for s in symbols}
    assert "calculate_orbit" in names
    assert "Spacecraft" in names


def test_subgraph_concurrency_locking() -> None:
    mgr = SubgraphLockManager()
    token_a = mgr.acquire_lock("worker_1", ["main.py", "utils.py"])
    assert token_a is not None
    assert mgr.is_locked("main.py")

    # Worker 2 attempts collision on utils.py
    token_b = mgr.acquire_lock("worker_2", ["utils.py", "config.py"])
    assert token_b is None

    # Worker 1 releases lock
    assert mgr.release_lock(token_a) is True
    assert not mgr.is_locked("main.py")

    # Worker 2 now succeeds
    token_b = mgr.acquire_lock("worker_2", ["utils.py", "config.py"])
    assert token_b is not None
    mgr.release_lock(token_b)


def test_diff_patcher_atomic_replace(tmp_path: Path) -> None:
    file = tmp_path / "greeting.py"
    file.write_text("def hello():\n    return 'world'\n", encoding="utf-8")

    res = DiffPatcher.apply_search_replace(
        file_path=file,
        search_block="return 'world'",
        replace_block="return 'keplix orbit'",
    )
    assert res.success is True
    assert "return 'keplix orbit'" in file.read_text(encoding="utf-8")

    # Non-matching block fails cleanly
    res_fail = DiffPatcher.apply_search_replace(
        file_path=file,
        search_block="non_existent_text",
        replace_block="foo",
    )
    assert res_fail.success is False


def test_log_pruner_redaction() -> None:
    pruner = LogPruner()
    raw = "Failed with token Bearer secret_token_value_12345 and sk-abc12345678901234567890"
    cleaned = pruner.redact_secrets(raw)
    assert "secret_token_value_12345" not in cleaned
    assert "[REDACTED_API_KEY]" in cleaned

