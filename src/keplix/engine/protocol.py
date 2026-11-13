"""Strict Protocol interface for the Keplix Code Engine.

Allows clean swapping between the pure-Python reference implementation
and the planned v0.2 Rust (PyO3/maturin + petgraph) drop-in accelerator.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Protocol, runtime_checkable


@dataclass
class CodeSymbol:
    """Represents an extracted code symbol (function, class, method, etc.)."""

    name: str
    kind: str  # "function", "class", "method", "variable", "interface"
    file_path: str
    start_line: int
    end_line: int
    signature: Optional[str] = None
    docstring: Optional[str] = None


@dataclass
class ImportStatement:
    """Represents a module or symbol import dependency."""

    source_module: str
    imported_names: list[str]
    file_path: str
    line_number: int
    is_relative: bool = False


@dataclass
class PatchResult:
    """Represents the atomic result of applying a search-and-replace or diff patch."""

    success: bool
    file_path: str
    applied: bool = False
    original_snippet: Optional[str] = None
    replaced_snippet: Optional[str] = None
    error: Optional[str] = None


@dataclass
class LockToken:
    """Represents an active concurrency lock held by an agent worker over subgraphs."""

    token_id: str
    agent_id: str
    locked_files: list[str]
    acquired_at: datetime = field(default_factory=datetime.utcnow)


@runtime_checkable
class CodeEngineProtocol(Protocol):
    """Protocol defining the required interface for Keplix code analysis and AST engines."""

    def parse_symbols(self, file_path: Path, content: str) -> list[CodeSymbol]:
        """Extract all top-level and nested AST symbols from source code."""
        ...

    def parse_imports(self, file_path: Path, content: str) -> list[ImportStatement]:
        """Extract import statements and dependency linkages."""
        ...

    def build_graph(self, root_dir: Path, ignore_patterns: Optional[list[str]] = None) -> None:
        """Scan workspace and construct internal dependency graph."""
        ...

    def get_blast_radius(self, modified_files: list[Path]) -> list[Path]:
        """Compute all downstream files directly or indirectly affected by changes."""
        ...

    def compute_repo_map(self, max_tokens: int = 2000) -> str:
        """Generate a PageRank-weighted symbol and file summary for LLM context."""
        ...

    def acquire_lock(self, agent_id: str, target_files: list[Path]) -> Optional[LockToken]:
        """Attempt to acquire a write lock on a subgraph of files."""
        ...

    def release_lock(self, token: LockToken) -> bool:
        """Release a previously acquired subgraph write lock."""
        ...

    def apply_patch(
        self,
        target_file: Path,
        search_block: str,
        replace_block: str,
    ) -> PatchResult:
        """Apply an atomic search-and-replace diff with validation."""
        ...

    def prune_logs(self, raw_logs: str, max_lines: int = 50) -> str:
        """Compress lengthy stack traces and redact potential credentials."""
        ...

