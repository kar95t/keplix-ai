"""Keplix configuration system using pydantic-settings, TOML loader, and env overrides."""

from pathlib import Path
import tomllib
from typing import Any, Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ExecutionConfig(BaseModel):
    """Runtime limits and container execution settings."""

    max_retries: int = Field(default=3, description="Maximum automated retry attempts per task")
    budget_usd: float = Field(default=2.50, description="Global budget threshold in USD")
    sandbox_image: str = Field(
        default="python:3.12-slim",
        description="Docker base image for ephemeral sandboxes",
    )
    state_dir: str = Field(
        default=".keplix",
        description="Directory for SQLite state checkpointing",
    )
    ignore_patterns: list[str] = Field(
        default_factory=lambda: [
            ".git",
            "__pycache__",
            ".pytest_cache",
            ".ruff_cache",
            "*.pyc",
            ".keplix",
            "node_modules",
            ".venv",
        ],
        description="Paths ignored during AST indexing and Git auto-commit",
    )


class ModelTierConfig(BaseModel):
    """Configuration for an individual model capability tier."""

    provider: str = Field(description="LLM provider name: 'anthropic', 'openai', 'deepseek', 'groq', 'ollama'")
    model_name: str = Field(description="Model identifier, e.g. 'claude-sonnet-4-5' or 'deepseek-chat'")
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None)
    base_url: Optional[str] = Field(default=None, description="Custom endpoint for Ollama or self-hosted API")
    api_key_env: Optional[str] = Field(default=None, description="Custom environment variable name for API key")


class KeplixSettings(BaseSettings):
    """Root Keplix settings model merging TOML, environment variables, and defaults."""

    model_config = SettingsConfigDict(
        env_prefix="KEPLIX_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    models: dict[str, ModelTierConfig] = Field(
        default_factory=lambda: {
            "architect": ModelTierConfig(
                provider="anthropic",
                model_name="claude-sonnet-4-5",
                temperature=0.2,
            ),
            "coder": ModelTierConfig(
                provider="deepseek",
                model_name="deepseek-chat",
                temperature=0.1,
            ),
            "fast": ModelTierConfig(
                provider="groq",
                model_name="llama-3.3-70b-versatile",
                temperature=0.0,
            ),
        }
    )


def load_settings(toml_path: Optional[Path] = None) -> KeplixSettings:
    """Load settings from a given or default keplix.toml path, layered with env vars."""
    target_path = toml_path or Path("keplix.toml")
    toml_data: dict[str, Any] = {}

    if target_path.is_file():
        try:
            with open(target_path, "rb") as f:
                toml_data = tomllib.load(f)
        except Exception as e:
            from keplix.cli.console import err_console

            err_console.print(f"[yellow]Warning: Could not parse {target_path}: {e}[/yellow]")

    return KeplixSettings(**toml_data)

