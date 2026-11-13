"""Model-agnostic chat model factory and OpenAI-compatible router."""

from typing import Any, Optional

from langchain_core.language_models.chat_models import BaseChatModel

from keplix.config.secrets import SecretManager
from keplix.config.settings import ModelTierConfig, load_settings

# Provider to environment variable name mapping
PROVIDER_ENV_KEYS: dict[str, str] = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "groq": "GROQ_API_KEY",
}


def create_chat_model(
    config: ModelTierConfig,
    secret_manager: Optional[SecretManager] = None,
    **kwargs: Any,
) -> BaseChatModel:
    """Instantiate a LangChain BaseChatModel based on ModelTierConfig.

    Supports native provider libraries or generic OpenAI-compatible base_url routing.
    """
    secrets = secret_manager or SecretManager()
    key_env = config.api_key_env or PROVIDER_ENV_KEYS.get(config.provider.lower())
    api_key = secrets.get_secret(key_env) if key_env else None

    provider = config.provider.lower()

    # Ollama or local self-hosted endpoint
    if provider == "ollama" or (config.base_url and "localhost" in config.base_url):
        from langchain_community.chat_models import ChatOllama

        return ChatOllama(
            model=config.model_name,
            temperature=config.temperature,
            base_url=config.base_url or "http://localhost:11434",
            **kwargs,
        )

    # Generic OpenAI-compatible router (DeepSeek, Groq, or custom base_url)
    if config.base_url or provider in ("deepseek", "groq"):
        from langchain_openai import ChatOpenAI

        base_url = config.base_url
        if not base_url:
            if provider == "deepseek":
                base_url = "https://api.deepseek.com/v1"
            elif provider == "groq":
                base_url = "https://api.groq.com/openai/v1"

        return ChatOpenAI(
            model=config.model_name,
            api_key=api_key or "placeholder",
            base_url=base_url,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            **kwargs,
        )

    # Standard LangChain init_chat_model resolution
    try:
        from langchain.chat_models import init_chat_model

        model_kwargs: dict[str, Any] = {
            "model_provider": provider,
            "temperature": config.temperature,
        }
        if api_key:
            model_kwargs["api_key"] = api_key
        if config.max_tokens:
            model_kwargs["max_tokens"] = config.max_tokens
        model_kwargs.update(kwargs)

        return init_chat_model(config.model_name, **model_kwargs)
    except Exception:
        # Fallback to direct langchain_openai
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=config.model_name,
            api_key=api_key or "placeholder",
            temperature=config.temperature,
            **kwargs,
        )


class ModelRouter:
    """Manages cached model instances per capability tier (architect, coder, fast)."""

    def __init__(self, secret_manager: Optional[SecretManager] = None) -> None:
        self.settings = load_settings()
        self.secrets = secret_manager or SecretManager()
        self._cache: dict[str, BaseChatModel] = {}

    def get_tier(self, tier_name: str) -> BaseChatModel:
        """Retrieve or initialize the model configured for a given tier."""
        if tier_name in self._cache:
            return self._cache[tier_name]

        if tier_name not in self.settings.models:
            raise KeyError(f"Capability tier '{tier_name}' not configured in keplix.toml")

        config = self.settings.models[tier_name]
        model = create_chat_model(config, secret_manager=self.secrets)
        self._cache[tier_name] = model
        return model

    @property
    def architect(self) -> BaseChatModel:
        return self.get_tier("architect")

    @property
    def coder(self) -> BaseChatModel:
        return self.get_tier("coder")

    @property
    def fast(self) -> BaseChatModel:
        return self.get_tier("fast")

