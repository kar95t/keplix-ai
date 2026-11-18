"""In-memory SetupContext and structured data models for the Keplix init wizard."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from keplix.cli.wizard.paths import WorkspacePaths
from keplix.config.settings import DomainConfig, KeplixSettings, PermissionConfig


class WorkspaceState(str, Enum):
    """Categorized status of a directory evaluated for a Keplix workspace."""

    FRESH_WORKSPACE = "fresh_workspace"
    """Neither keplix.toml nor .keplix/ runtime directory exists."""

    EXISTING_WORKSPACE = "existing_workspace"
    """Both keplix.toml and .keplix/ exist and configuration is valid."""

    EXISTING_CONFIGURATION = "existing_configuration"
    """keplix.toml exists and is valid, but .keplix/ directory is missing."""

    PARTIAL_RUNTIME = "partial_runtime"
    """.keplix/ directory exists, but keplix.toml is missing."""

    INVALID_CONFIGURATION = "invalid_configuration"
    """keplix.toml exists but failed syntax or Pydantic validation."""


@dataclass
class EnvironmentInfo:
    """Read-only system and workspace environment detection results."""

    # Operating system
    os_name: str  # "Windows", "macOS", "Linux", "Unknown"
    os_version: str

    # Python interpreter
    python_version: str
    python_executable: str
    python_supported: bool
    python_req: str = ">=3.12"

    # Current working directory
    cwd: Path = field(default_factory=Path.cwd)
    cwd_readable: bool = True
    cwd_writable: bool = True

    # Git version control (optional)
    git_available: bool = False
    git_version: Optional[str] = None
    is_git_repo: bool = False
    git_root: Optional[Path] = None
    git_branch: Optional[str] = None
    git_detached: bool = False

    # Docker execution backend (optional)
    docker_cli_available: bool = False
    docker_cli_version: Optional[str] = None
    docker_daemon_running: bool = False
    docker_server_version: Optional[str] = None

    # Keplix package verification
    keplix_version: str = "0.1.0"
    keplix_importable: bool = True

    # Workspace artifact presence
    has_toml: bool = False
    has_runtime: bool = False
    has_gitignore: bool = False

    # Credential management (keyring)
    keyring_available: bool = False
    keyring_backend: Optional[str] = None
    keyring_priority: int = 0
    keyring_usable: bool = False

    # Provider API key presence (presence boolean ONLY, never values!)
    provider_keys: dict[str, bool] = field(default_factory=dict)

    # Aggregated status
    all_required_passed: bool = True
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class WorkspaceInspectionResult:
    """Structured inspection result from the common workspace inspection service."""

    canonical_path: Path
    is_newly_created: bool = False

    # Git status
    has_git: bool = False
    git_branch: Optional[str] = None

    # Artifact presence
    has_toml: bool = False
    has_runtime: bool = False
    has_gitignore: bool = False

    # Configuration validity
    is_config_valid: bool = False
    existing_config: Optional[KeplixSettings] = None
    raw_config_text: Optional[str] = None
    validation_errors: list[str] = field(default_factory=list)

    # Resolved workspace state
    state: WorkspaceState = WorkspaceState.FRESH_WORKSPACE


@dataclass
class SetupContext:
    """Central in-memory state passed across wizard stages (Steps 0–8).

    Guarantees no plaintext secrets or credentials are ever recorded.
    """

    env_info: Optional[EnvironmentInfo] = None
    selected_path: Optional[Path] = None
    paths: Optional[WorkspacePaths] = None
    selection_method: Optional[str] = None  # "current", "choose", "create"
    inspection: Optional[WorkspaceInspectionResult] = None

    # Action chosen if existing configuration detected
    config_action: Optional[str] = None  # "continue", "review", "reconfigure", "preserve"

    # Workspace status flags
    is_new_workspace: bool = False
    is_partial_workspace: bool = False
    cancelled: bool = False

    # Wizard stage tracking (total_steps is configurable)
    current_step: int = 0
    total_steps: int = 9

    # Step 3: Domain Pack Selection
    domains: Optional[DomainConfig] = None

    # Step 4: Capabilities and Permissions
    permissions: Optional[PermissionConfig] = None

    def set_workspace_path(self, path: Path, method: str, is_new: bool = False) -> None:
        """Set the canonical workspace path and derive immutable WorkspacePaths."""
        resolved = path.resolve()
        self.selected_path = resolved
        self.paths = WorkspacePaths(root=resolved)
        self.selection_method = method
        self.is_new_workspace = is_new

