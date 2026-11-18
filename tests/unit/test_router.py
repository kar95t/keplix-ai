"""Unit tests for model router and tier configurations."""

import os
import unittest
from unittest.mock import patch

try:
    from keplix.config.secrets import SecretManager
    from keplix.config.settings import ModelTierConfig
    from keplix.llm.factory import create_chat_model
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False


class TestRouter(unittest.TestCase):
    @unittest.skipUnless(HAS_DEPS, "LLM factory or LangChain dependencies not installed")
    def test_custom_endpoint_model_creation(self) -> None:
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "mock_key"}):
            config = ModelTierConfig(
                provider="deepseek",
                model_name="deepseek-chat",
                temperature=0.1,
            )
            sm = SecretManager()
            model = create_chat_model(config, secret_manager=sm)
            self.assertIsNotNone(model)

