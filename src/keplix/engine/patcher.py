"""Atomic search-and-replace diff engine with pre-validation and rollback support."""

import difflib
from pathlib import Path
from typing import Optional

from keplix.engine.protocol import PatchResult


class DiffPatcher:
    """Safely and atomically applies targeted diffs and search-and-replace edits to files."""

    @staticmethod
    def apply_search_replace(
        file_path: Path,
        search_block: str,
        replace_block: str,
        create_if_missing: bool = False,
    ) -> PatchResult:
        """Atomically find `search_block` in `file_path` and replace with `replace_block`.

        Fails cleanly if `search_block` is not found or is ambiguous.
        """
        if not file_path.exists():
            if create_if_missing and not search_block.strip():
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(replace_block, encoding="utf-8")
                return PatchResult(
                    success=True,
                    file_path=str(file_path),
                    applied=True,
                    replaced_snippet=replace_block,
                )
            return PatchResult(
                success=False,
                file_path=str(file_path),
                error=f"File {file_path} does not exist.",
            )

        content = file_path.read_text(encoding="utf-8", errors="replace")

        # Standardize line endings for matching
        norm_content = content.replace("\r\n", "\n")
        norm_search = search_block.replace("\r\n", "\n")
        norm_replace = replace_block.replace("\r\n", "\n")

        count = norm_content.count(norm_search)
        if count == 0:
            # Fuzzy match attempt: strip outer whitespace
            stripped_search = norm_search.strip()
            if stripped_search and stripped_search in norm_content:
                norm_search = stripped_search
                count = norm_content.count(norm_search)

        if count == 0:
            return PatchResult(
                success=False,
                file_path=str(file_path),
                error="Target search block was not found in file.",
            )

        if count > 1:
            return PatchResult(
                success=False,
                file_path=str(file_path),
                error=f"Ambiguous replacement: target block occurs {count} times in file.",
            )

        # Atomic replacement
        new_content = norm_content.replace(norm_search, norm_replace, 1)

        # Preserve original line endings if file was CRLF
        if "\r\n" in content:
            new_content = new_content.replace("\n", "\r\n")

        # Write to temporary adjacent file then replace atomically
        tmp_file = file_path.with_suffix(f"{file_path.suffix}.tmp")
        try:
            tmp_file.write_text(new_content, encoding="utf-8")
            tmp_file.replace(file_path)
        except Exception as e:
            if tmp_file.exists():
                tmp_file.unlink()
            return PatchResult(
                success=False,
                file_path=str(file_path),
                error=f"Failed to write patch atomically: {e}",
            )

        return PatchResult(
            success=True,
            file_path=str(file_path),
            applied=True,
            original_snippet=search_block,
            replaced_snippet=replace_block,
        )

    @staticmethod
    def generate_diff(file_path: Path, old_text: str, new_text: str) -> str:
        """Generate a standard unified diff between two text versions."""
        return "".join(
            difflib.unified_diff(
                old_text.splitlines(keepends=True),
                new_text.splitlines(keepends=True),
                fromfile=f"a/{file_path.name}",
                tofile=f"b/{file_path.name}",
            )
        )

