"""LangChain @tool wrappers around Keplix Code Engine (AST graph, symbols, and diffs)."""

from pathlib import Path
from typing import Optional

from langchain_core.tools import tool

from keplix.engine.index import RepoMapIndexer
from keplix.engine.parser import ASTParser
from keplix.engine.patcher import DiffPatcher
from keplix.tools.registry import register_tool


@tool
def read_workspace_file(file_path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> str:
    """Read contents of a workspace file, optionally sliced between line numbers."""
    target = Path(file_path)
    if not target.exists():
        return f"Error: File '{file_path}' does not exist."
    try:
        lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
        start = (start_line - 1) if start_line and start_line > 0 else 0
        end = end_line if end_line else len(lines)
        sliced = lines[start:end]
        return "\n".join(f"{i + start + 1}: {line}" for i, line in enumerate(sliced))
    except Exception as e:
        return f"Error reading file '{file_path}': {e}"


@tool
def get_file_symbols(file_path: str) -> str:
    """Extract AST symbols (functions, classes, signatures) from a specific file."""
    target = Path(file_path)
    if not target.exists():
        return f"Error: File '{file_path}' does not exist."
    try:
        content = target.read_text(encoding="utf-8", errors="replace")
        parser = ASTParser()
        symbols = parser.parse_symbols(target, content)
        if not symbols:
            return f"No symbols extracted from '{file_path}'."
        out = [f"Symbols in {file_path}:"]
        for s in symbols:
            sig = f": {s.signature}" if s.signature else ""
            out.append(f"  • [{s.kind}] {s.name}{sig} (lines {s.start_line}-{s.end_line})")
        return "\n".join(out)
    except Exception as e:
        return f"Error extracting symbols from '{file_path}': {e}"


@tool
def query_blast_radius(file_paths: list[str]) -> str:
    """Query the AST dependency graph to find all downstream files impacted by changes."""
    try:
        indexer = RepoMapIndexer(Path.cwd())
        dep_graph = indexer.build_index()
        impacted = dep_graph.get_blast_radius(file_paths)
        if not impacted:
            return "No downstream dependencies detected in graph."
        return f"Impacted blast-radius files ({len(impacted)}): \n" + "\n".join(f"  • {f}" for f in impacted)
    except Exception as e:
        return f"Error computing blast radius: {e}"


@tool
def apply_diff_patch(file_path: str, search_block: str, replace_block: str) -> str:
    """Atomically replace search_block with replace_block in the target file."""
    target = Path(file_path)
    result = DiffPatcher.apply_search_replace(
        file_path=target,
        search_block=search_block,
        replace_block=replace_block,
        create_if_missing=True,
    )
    if result.success:
        return f"Successfully patched {file_path}."
    return f"Failed to patch {file_path}: {result.error}"


# Auto-register code engine tools
register_tool(scope="code")(read_workspace_file)
register_tool(scope="code")(get_file_symbols)
register_tool(scope="code")(query_blast_radius)
register_tool(scope="code")(apply_diff_patch)

