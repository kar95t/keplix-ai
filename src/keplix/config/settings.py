"""Keplix configuration system using pydantic-settings, TOML loader, and env overrides."""

from enum import Enum
from pathlib import Path
import tomllib
from typing import Any, Optional, Union

try:
    from pydantic import BaseModel, Field
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:
    class BaseModel:  # type: ignore[no-redef]
        def __init__(self, **kwargs: Any) -> None:
            for k, v in kwargs.items():
                setattr(self, k, v)
        def model_dump(self) -> dict[str, Any]:
            res: dict[str, Any] = {}
            for k, v in self.__dict__.items():
                if hasattr(v, "model_dump"):
                    res[k] = v.model_dump()
                elif hasattr(v, "value"):
                    res[k] = v.value
                else:
                    res[k] = v
            return res

    class BaseSettings(BaseModel):  # type: ignore[no-redef]
        pass

    def Field(default: Any = None, default_factory: Any = None, **kwargs: Any) -> Any:  # type: ignore[no-redef]
        if default_factory is not None:
            return default_factory()
        return default

    def SettingsConfigDict(**kwargs: Any) -> dict[str, Any]:  # type: ignore[no-redef]
        return kwargs


# ---------------------------------------------------------------------------
# Step 3: Domain Pack Enums & Models
# ---------------------------------------------------------------------------

class DomainMode(str, Enum):
    AUTO = "auto"
    SPECIALIZED = "specialized"
    CORE_ONLY = "core_only"


class DomainConfig(BaseModel):
    """Configuration for specialized knowledge and capability domain packs."""

    mode: DomainMode = Field(default=DomainMode.AUTO, description="Domain mode: 'auto', 'specialized', or 'core_only'")
    enabled: list[str] = Field(default_factory=list, description="List of enabled domain pack identifiers")


# ---------------------------------------------------------------------------
# Step 4: Capability & Permission Enums & Models
# ---------------------------------------------------------------------------

class PermissionAction(str, Enum):
    ALLOW = "allow"
    APPROVAL = "approval"
    SANDBOX = "sandbox"
    DENY = "deny"


class NetworkMode(str, Enum):
    DISABLED = "disabled"
    ALLOWLIST = "allowlist"
    UNRESTRICTED = "unrestricted"


class FilesystemPermissions(BaseModel):
    """Filesystem read, write, and deletion access policies."""

    read_workspace: PermissionAction = Field(default=PermissionAction.ALLOW)
    create_files: PermissionAction = Field(default=PermissionAction.ALLOW)
    modify_files: PermissionAction = Field(default=PermissionAction.ALLOW)
    delete_files: PermissionAction = Field(default=PermissionAction.APPROVAL)
    access_outside_workspace: PermissionAction = Field(default=PermissionAction.APPROVAL)


class ExecutionPermissions(BaseModel):
    """Command, testing, package installation, and Git execution policies."""

    terminal_commands: PermissionAction = Field(default=PermissionAction.SANDBOX)
    run_tests: PermissionAction = Field(default=PermissionAction.ALLOW)
    install_dependencies: PermissionAction = Field(default=PermissionAction.APPROVAL)
    git_commit: PermissionAction = Field(default=PermissionAction.APPROVAL)
    git_push: PermissionAction = Field(default=PermissionAction.APPROVAL)


class NetworkPermissions(BaseModel):
    """Outbound network policy and domain whitelist."""

    mode: NetworkMode = Field(default=NetworkMode.ALLOWLIST)
    allowed_domains: list[str] = Field(
        default_factory=lambda: ["pypi.org", "files.pythonhosted.org"]
    )


class ExternalActionPermissions(BaseModel):
    """External side-effect actions requiring safety barriers."""

    deployment: PermissionAction = Field(default=PermissionAction.APPROVAL)
    publishing: PermissionAction = Field(default=PermissionAction.APPROVAL)
    sending_emails: PermissionAction = Field(default=PermissionAction.APPROVAL)
    destructive_actions: PermissionAction = Field(default=PermissionAction.APPROVAL)


class PermissionProfile(str, Enum):
    RESTRICTED = "restricted"
    BALANCED = "balanced"
    AUTONOMOUS = "autonomous"
    CUSTOM = "custom"


class PermissionConfig(BaseModel):
    """Root permissions model governing agent execution capabilities."""

    profile: PermissionProfile = Field(default=PermissionProfile.BALANCED)
    filesystem: FilesystemPermissions = Field(default_factory=FilesystemPermissions)
    execution: ExecutionPermissions = Field(default_factory=ExecutionPermissions)
    network: NetworkPermissions = Field(default_factory=NetworkPermissions)
    external_actions: ExternalActionPermissions = Field(default_factory=ExternalActionPermissions)


def resolve_profile_permissions(profile: Union[PermissionProfile, str]) -> PermissionConfig:
    """Resolve a profile name into concrete, typed permission defaults."""
    if isinstance(profile, str):
        profile = PermissionProfile(profile.lower())

    if profile == PermissionProfile.RESTRICTED:
        return PermissionConfig(
            profile=PermissionProfile.RESTRICTED,
            filesystem=FilesystemPermissions(
                read_workspace=PermissionAction.ALLOW,
                create_files=PermissionAction.APPROVAL,
                modify_files=PermissionAction.APPROVAL,
                delete_files=PermissionAction.APPROVAL,
                access_outside_workspace=PermissionAction.APPROVAL,
            ),
            execution=ExecutionPermissions(
                terminal_commands=PermissionAction.APPROVAL,
                run_tests=PermissionAction.APPROVAL,
                install_dependencies=PermissionAction.APPROVAL,
                git_commit=PermissionAction.APPROVAL,
                git_push=PermissionAction.APPROVAL,
            ),
            network=NetworkPermissions(
                mode=NetworkMode.DISABLED,
                allowed_domains=[],
            ),
            external_actions=ExternalActionPermissions(
                deployment=PermissionAction.APPROVAL,
                publishing=PermissionAction.APPROVAL,
                sending_emails=PermissionAction.APPROVAL,
                destructive_actions=PermissionAction.APPROVAL,
            ),
        )
    elif profile == PermissionProfile.AUTONOMOUS:
        return PermissionConfig(
            profile=PermissionProfile.AUTONOMOUS,
            filesystem=FilesystemPermissions(
                read_workspace=PermissionAction.ALLOW,
                create_files=PermissionAction.ALLOW,
                modify_files=PermissionAction.ALLOW,
                delete_files=PermissionAction.SANDBOX,
                access_outside_workspace=PermissionAction.APPROVAL,
            ),
            execution=ExecutionPermissions(
                terminal_commands=PermissionAction.SANDBOX,
                run_tests=PermissionAction.ALLOW,
                install_dependencies=PermissionAction.SANDBOX,
                git_commit=PermissionAction.ALLOW,
                git_push=PermissionAction.APPROVAL,
            ),
            network=NetworkPermissions(
                mode=NetworkMode.ALLOWLIST,
                allowed_domains=["pypi.org", "files.pythonhosted.org"],
            ),
            external_actions=ExternalActionPermissions(
                deployment=PermissionAction.APPROVAL,
                publishing=PermissionAction.APPROVAL,
                sending_emails=PermissionAction.APPROVAL,
                destructive_actions=PermissionAction.APPROVAL,
            ),
        )
    elif profile == PermissionProfile.CUSTOM:
        cfg = resolve_profile_permissions(PermissionProfile.BALANCED)
        cfg.profile = PermissionProfile.CUSTOM
        return cfg
    else:  # BALANCED (recommended default)
        return PermissionConfig(
            profile=PermissionProfile.BALANCED,
            filesystem=FilesystemPermissions(
                read_workspace=PermissionAction.ALLOW,
                create_files=PermissionAction.ALLOW,
                modify_files=PermissionAction.ALLOW,
                delete_files=PermissionAction.APPROVAL,
                access_outside_workspace=PermissionAction.APPROVAL,
            ),
            execution=ExecutionPermissions(
                terminal_commands=PermissionAction.SANDBOX,
                run_tests=PermissionAction.ALLOW,
                install_dependencies=PermissionAction.APPROVAL,
                git_commit=PermissionAction.APPROVAL,
                git_push=PermissionAction.APPROVAL,
            ),
            network=NetworkPermissions(
                mode=NetworkMode.ALLOWLIST,
                allowed_domains=["pypi.org", "files.pythonhosted.org"],
            ),
            external_actions=ExternalActionPermissions(
                deployment=PermissionAction.APPROVAL,
                publishing=PermissionAction.APPROVAL,
                sending_emails=PermissionAction.APPROVAL,
                destructive_actions=PermissionAction.APPROVAL,
            ),
        )


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

    domains: DomainConfig = Field(default_factory=DomainConfig)
    permissions: PermissionConfig = Field(default_factory=PermissionConfig)
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
            # Support both [domain] and [domains] in TOML
            if "domain" in toml_data and "domains" not in toml_data:
                toml_data["domains"] = toml_data["domain"]
        except Exception as e:
            from keplix.cli.console import err_console

            err_console.print(f"[yellow]Warning: Could not parse {target_path}: {e}[/yellow]")

    return KeplixSettings(**toml_data)

