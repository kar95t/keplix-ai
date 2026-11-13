"""Rich console output helpers, spinners, diff renderers, and live status trees."""

from collections.abc import Generator
from contextlib import contextmanager
import difflib
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.tree import Tree

console = Console()
err_console = Console(stderr=True)


def print_banner() -> None:
    """Print the Keplix mission control startup banner."""
    banner = (
        "[bold cyan]🛰️  KEPLIX MISSION CONTROL[/bold cyan] "
        "[dim]| Multi-Agent Orchestration Harness[/dim]\n"
        "[dim italic]\"Keeping non-deterministic models locked in deterministic orbits\"[/dim italic]"
    )
    console.print(Panel(banner, border_style="cyan", expand=False))


@contextmanager
def status_spinner(message: str) -> Generator[None, None, None]:
    """Display an active spinner context for long-running agent or sandbox operations."""
    with console.status(f"[bold green]{message}[/bold green]", spinner="dots") as status:
        yield status


def render_diff(filepath: str, old_content: str, new_content: str) -> None:
    """Render an atomic syntax-highlighted diff between original and proposed file contents."""
    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)
    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=f"a/{filepath}",
        tofile=f"b/{filepath}",
        lineterm="",
    )
    diff_text = "".join(diff)
    if not diff_text.strip():
        console.print(f"[dim]No changes in {filepath}[/dim]")
        return

    syntax = Syntax(diff_text, "diff", theme="monokai", line_numbers=True)
    console.print(Panel(syntax, title=f"[bold yellow]Diff: {filepath}[/bold yellow]", expand=False))


def create_agent_tree(root_label: str, agent_statuses: dict[str, Any]) -> Tree:
    """Create a hierarchical Rich tree visualization of agent statuses and subtasks."""
    tree = Tree(f"[bold cyan]{root_label}[/bold cyan]")
    for agent_id, info in agent_statuses.items():
        status_color = "green" if info.get("status") == "completed" else "yellow"
        branch = tree.add(f"[bold {status_color}]{agent_id}[/bold {status_color}] - {info.get('role', 'worker')}")
        if "target_files" in info:
            targets = branch.add("[dim]Locked Targets[/dim]")
            for target in info["target_files"]:
                targets.add(f"[italic]{target}[/italic]")
        if "action" in info:
            branch.add(f"[dim]Current action:[/dim] {info['action']}")
    return tree


def render_table(title: str, columns: list[str], rows: list[list[str]]) -> None:
    """Render a structured status table."""
    table = Table(title=title, border_style="dim")
    for col in columns:
        table.add_column(col, style="cyan")
    for row in rows:
        table.add_row(*row)
    console.print(table)

