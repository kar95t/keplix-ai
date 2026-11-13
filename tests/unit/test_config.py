"""Unit tests for Keplix configuration and secret management."""

from pathlib import Path

from keplix.config.secrets import SecretManager
from keplix.config.settings import KeplixSettings, load_settings


def test_default_settings_instantiation() -> None:
    settings = KeplixSettings()
    assert settings.execution.max_retries == 3
    assert settings.execution.budget_usd == 2.50
    assert "architect" in settings.models
    assert "coder" in settings.models
    assert "fast" in settings.models


def test_toml_loading(tmp_path: Path) -> None:
    toml_file = tmp_path / "keplix.toml"
    toml_file.write_text(
        """
[execution]
max_retries = 5
budget_usd = 10.00
sandbox_image = "python:3.12-alpine"

[models.architect]
provider = "openai"
model_name = "gpt-4o"
""",
        encoding="utf-8",
    )

    settings = load_settings(toml_file)
    assert settings.execution.max_retries == 5
    assert settings.execution.budget_usd == 10.00
    assert settings.execution.sandbox_image == "python:3.12-alpine"
    assert settings.models["architect"].model_name == "gpt-4o"


def test_secret_manager_env_priority(monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test_key_123")
    sm = SecretManager()
    val = sm.get_secret("ANTHROPIC_API_KEY", prompt_user=False)
    assert val == "test_key_123"

