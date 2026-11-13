"""Unit tests for model router and tier configurations."""

from keplix.config.secrets import SecretManager
from keplix.config.settings import ModelTierConfig
from keplix.llm.factory import create_chat_model


def test_custom_endpoint_model_creation(monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "mock_key")
    config = ModelTierConfig(
        provider="deepseek",
        model_name="deepseek-chat",
        temperature=0.1,
    )
    sm = SecretManager()
    model = create_chat_model(config, secret_manager=sm)
    assert model is not None

