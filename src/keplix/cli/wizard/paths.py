"""Immutable workspace paths manager for Keplix workspaces."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WorkspacePaths:
    """Immutable collection of canonical filesystem paths for a Keplix workspace.

    Derives all configuration and runtime artifact paths from a canonical workspace root.
    Note: Instantiating this class must NEVER create directories or files automatically.
    """

    root: Path

    def __post_init__(self) -> None:
        # Enforce resolved absolute canonical path
        object.__setattr__(self, "root", self.root.resolve())

    @property
    def config_file(self) -> Path:
        """Primary project configuration file (keplix.toml)."""
        return self.root / "keplix.toml"

    @property
    def runtime_dir(self) -> Path:
        """Internal runtime state directory (.keplix/)."""
        return self.root / ".keplix"

    @property
    def state_db(self) -> Path:
        """SQLite persistence database (.keplix/state.db)."""
        return self.runtime_dir / "state.db"

    @property
    def runs_dir(self) -> Path:
        """Orchestration execution records (.keplix/runs/)."""
        return self.runtime_dir / "runs"

    @property
    def logs_dir(self) -> Path:
        """Execution logs and stack trace archives (.keplix/logs/)."""
        return self.runtime_dir / "logs"

    @property
    def traces_dir(self) -> Path:
        """Web replayer trace and graph export artifacts (.keplix/traces/)."""
        return self.runtime_dir / "traces"

    @property
    def cache_dir(self) -> Path:
        """Cached AST trees and intermediate data (.keplix/cache/)."""
        return self.runtime_dir / "cache"

    @property
    def indexes_dir(self) -> Path:
        """Serialized AST symbol dependency graphs (.keplix/indexes/)."""
        return self.runtime_dir / "indexes"

    @property
    def gitignore_file(self) -> Path:
        """Project gitignore file (.gitignore)."""
        return self.root / ".gitignore"

