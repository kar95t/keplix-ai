"""Common read-only workspace inspection service shared across wizard options."""

from pathlib import Path
import tomllib
from typing import Optional

try:
    from pydantic import ValidationError
except ImportError:
    class ValidationError(Exception):  # type: ignore[no-redef]
        def errors(self) -> list[dict]:
            return []

from keplix.cli.wizard.context import WorkspaceInspectionResult, WorkspaceState
from keplix.cli.wizard.detector import detect_git
from keplix.config.settings import KeplixSettings


class WorkspaceInspector:
    """Read-only service to inspect and evaluate any candidate directory for a Keplix workspace."""

    @staticmethod
    def inspect(
        path: Path,
        is_newly_created: bool = False,
    ) -> WorkspaceInspectionResult:
        """Inspect a directory to evaluate artifact presence and configuration validity.

        Never creates, modifies, or deletes files or directories.
        """
        canonical = path.resolve()

        # Artifact presence
        toml_path = canonical / "keplix.toml"
        runtime_path = canonical / ".keplix"
        gitignore_path = canonical / ".gitignore"

        has_toml = toml_path.is_file()
        has_runtime = runtime_path.is_dir()
        has_gitignore = gitignore_path.is_file()

        # Git status
        _, _, is_git_repo, _, git_branch, _ = detect_git(canonical)

        # TOML validation
        is_config_valid = False
        existing_config: Optional[KeplixSettings] = None
        raw_config_text: Optional[str] = None
        validation_errors: list[str] = []

        if has_toml:
            try:
                raw_config_text = toml_path.read_text(encoding="utf-8", errors="replace")
                data = tomllib.loads(raw_config_text)
                # Validate against official KeplixSettings schema
                existing_config = KeplixSettings(**data)
                is_config_valid = True
            except tomllib.TOMLDecodeError as err:
                is_config_valid = False
                validation_errors.append(f"TOML Syntax Error: {err}")
            except ValidationError as err:
                is_config_valid = False
                for e in err.errors():
                    loc = " -> ".join(str(p) for p in e["loc"])
                    validation_errors.append(f"Validation Error at '{loc}': {e['msg']}")
            except Exception as err:
                is_config_valid = False
                validation_errors.append(f"Failed to read keplix.toml: {err}")

        # Resolve Workspace State based on specification table
        if has_toml and not is_config_valid:
            state = WorkspaceState.INVALID_CONFIGURATION
        elif has_toml and is_config_valid and has_runtime:
            state = WorkspaceState.EXISTING_WORKSPACE
        elif has_toml and is_config_valid and not has_runtime:
            state = WorkspaceState.EXISTING_CONFIGURATION
        elif not has_toml and has_runtime:
            state = WorkspaceState.PARTIAL_RUNTIME
        else:
            state = WorkspaceState.FRESH_WORKSPACE

        return WorkspaceInspectionResult(
            canonical_path=canonical,
            is_newly_created=is_newly_created,
            has_git=is_git_repo,
            git_branch=git_branch,
            has_toml=has_toml,
            has_runtime=has_runtime,
            has_gitignore=has_gitignore,
            is_config_valid=is_config_valid,
            existing_config=existing_config,
            raw_config_text=raw_config_text,
            validation_errors=validation_errors,
            state=state,
        )
