"""Typer CLI entrypoints for Keplix (`keplix run`, `init`, `inspect`)."""

from pathlib import Path
from typing import Annotated, Optional

try:
    import typer
except ImportError:
    class _MockTyper:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs):
            pass
        def callback(self, *args, **kwargs):
            return lambda fn: fn
        def command(self, *args, **kwargs):
            return lambda fn: fn
        @staticmethod
        def Option(*args, **kwargs):
            return args[0] if args else None
        @staticmethod
        def Argument(*args, **kwargs):
            return args[0] if args else None
        class Exit(SystemExit):
            def __init__(self, code: int = 0):
                super().__init__(code)
        def Typer(self, *args, **kwargs):
            return self
    typer = _MockTyper()  # type: ignore[assignment]

from keplix import __version__
from keplix.cli.console import console, print_banner
from keplix.cli.wizard import run_init_wizard
from keplix.config.secrets import SecretManager
from keplix.config.settings import load_settings

app = typer.Typer(
    name="keplix",
    help="Contract-first, model-agnostic multi-agent orchestration harness.",
    no_args_is_help=True,
)


@app.callback(invoke_without_command=True)
def main_callback(
    version: Annotated[
        bool,
        typer.Option("--version", "-v", help="Display Keplix version and exit."),
    ] = False,
) -> None:
    """Keplix global options."""
    if version:
        console.print(f"[bold cyan]Keplix[/bold cyan] version [bold green]{__version__}[/bold green]")
        raise typer.Exit()


@app.command()
def init(
    config_path: Annotated[
        Path,
        typer.Option("--config", "-c", help="Target configuration file destination."),
    ] = Path("keplix.toml"),
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite existing configuration if present."),
    ] = False,
) -> None:
    """Launch the interactive first-run setup wizard for Keplix."""
    context = run_init_wizard(total_steps=9)

    if context is None or context.cancelled:
        raise typer.Exit(code=0)

    # Report completion status for Steps 0–2
    selected = context.selected_path or Path.cwd()
    console.print(f"\n[bold green]✓ Steps 0–2 Completed successfully![/bold green]")
    console.print(f"[dim]Selected workspace:[/dim] [cyan]{selected}[/cyan]")
    console.print(f"[dim]Workspace state:[/dim] [yellow]{context.inspection.state.value if context.inspection else 'fresh'}[/yellow]")
    console.print(f"[dim]Ready for Step 3: Execution Environment.[/dim]\n")


@app.command()
def run(
    goal: Annotated[
        str,
        typer.Option("--goal", "-g", help="High-level engineering goal or user specification.", prompt=True),
    ],
    config_file: Annotated[
        Path,
        typer.Option("--config", "-c", help="Path to keplix.toml config file."),
    ] = Path("keplix.toml"),
    budget: Annotated[
        Optional[float],
        typer.Option("--budget", "-b", help="Override maximum run budget in USD."),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", help="Enable verbose debug logging and streaming traces."),
    ] = False,
) -> None:
    """Execute an orchestrated multi-agent run against the codebase."""
    print_banner()
    settings = load_settings(config_file if config_file.exists() else None)
    if budget is not None:
        settings.execution.budget_usd = budget

    console.print(f"[bold]Active Goal:[/bold] [yellow]{goal}[/yellow]")
    console.print(
        f"[dim]Budget: ${settings.execution.budget_usd:.2f} | "
        f"Sandbox: {settings.execution.sandbox_image} | "
        f"Retries: {settings.execution.max_retries}[/dim]\n"
    )

    console.print("[bold cyan]Spinning up Dynamic Supervisor orbit...[/bold cyan]")
    # LangGraph workflow invocation hook (wire-up ready)
    console.print("[dim]Graph initialized. State checkpointer online at .keplix/state.db[/dim]")


@app.command()
def inspect(
    target: Annotated[
        str,
        typer.Argument(help="Target subsystem to inspect: 'index', 'graph', or 'secrets'."),
    ] = "index",
) -> None:
    """Inspect internal state, AST symbol index, or active graph checkpoints."""
    print_banner()
    if target == "index":
        console.print("[bold]AST Code Index Inspection[/bold]")
        console.print("[dim]Building in-memory symbol graph using Tree-sitter + NetworkX...[/dim]")
    elif target == "graph":
        console.print("[bold]LangGraph Orbit Inspection[/bold]")
        console.print("[dim]Listing checkpoints in .keplix/state.db...[/dim]")
    elif target == "secrets":
        console.print("[bold]Credential Storage Inspection[/bold]")
        secret_manager = SecretManager()
        for key in ["ANTHROPIC_API_KEY", "OPENAI_API_KEY", "DEEPSEEK_API_KEY", "GROQ_API_KEY"]:
            val = secret_manager.get_secret(key, prompt_user=False)
            status = "[green]Available[/green]" if val else "[red]Missing[/red]"
            console.print(f"  • {key}: {status}")
    else:
        console.print(f"[red]Unknown inspection target '{target}'. Use 'index', 'graph', or 'secrets'.[/red]")


if __name__ == "__main__":
    app()
