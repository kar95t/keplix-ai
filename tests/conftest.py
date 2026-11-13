"""Global pytest configuration and fixtures for Keplix test suites."""

from pathlib import Path
import tempfile
from typing import Generator

import pytest

from keplix.config.settings import ExecutionConfig, KeplixSettings, ModelTierConfig
from keplix.engine.locks import SubgraphLockManager
from keplix.engine.parser import ASTParser


@pytest.fixture
def temp_workspace() -> Generator[Path, None, None]:
    """Provide a temporary directory behaving as an isolated workspace."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        workspace = Path(tmp_dir)
        # Create a sample python file
        sample_file = workspace / "math_utils.py"
        sample_file.write_text(
            "import math\n\ndef add(a, b):\n    '''Add two numbers.'''\n    return a + b\n\nclass Calculator:\n    def multiply(self, x, y):\n        return x * y\n",
            encoding="utf-8",
        )
        yield workspace


@pytest.fixture
def ast_parser() -> ASTParser:
    return ASTParser()


@pytest.fixture
def lock_manager() -> SubgraphLockManager:
    return SubgraphLockManager()


@pytest.fixture
def mock_settings() -> KeplixSettings:
    return KeplixSettings(
        execution=ExecutionConfig(max_retries=2, budget_usd=1.00),
        models={
            "architect": ModelTierConfig(provider="anthropic", model_name="claude-3-haiku-20240307"),
            "coder": ModelTierConfig(provider="deepseek", model_name="deepseek-chat"),
            "fast": ModelTierConfig(provider="groq", model_name="llama-3.1-8b-instant"),
        },
    )

