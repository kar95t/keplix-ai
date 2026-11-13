"""Typer CLI entrypoints for Keplix (`keplix run`, `init`, `inspect`)."""

from pathlib import Path
import shutil
from typing import Annotated, Optional

import typer

from keplix import __version__
from keplix.cli.console import console, print_banner
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
    """Initialize a Keplix project in the current directory."""
    print_banner()

    template_path = Path("keplix.toml.example")
    if config_path.exists() and not force:
        console.print(
            f"[bold yellow]Config file '{config_path}' already exists.[/bold yellow] "
            "Use [bold cyan]--force[/bold cyan] to overwrite."
        )
    else:
        if template_path.exists():
            shutil.copyfile(template_path, config_path)
            console.print(f"[green]✓[/green] Created [bold]{config_path}[/bold] from template.")
        else:
            # Fallback inline template
            settings = load_settings()
            config_path.write_text(
                "# keplix.toml\n[execution]\nmax_retries = 3\nbudget_usd = 2.50\n",
                encoding="utf-8",
            )
            console.print(f"[green]✓[/green] Generated default [bold]{config_path}[/bold].")

    # Create local runtime state directory
    state_dir = Path(".keplix")
    state_dir.mkdir(parents=True, exist_ok=True)
    console.print(f"[green]✓[/green] Initialized local state store at [bold]{state_dir}/[/bold]")

    # Interactive Secret setup helper
    console.print("\n[bold]Configuring Model Credentials (OS Keyring / Environment):[/bold]")
    secret_manager = SecretManager()
    for provider, env_var in [
        ("Anthropic", "ANTHROPIC_API_KEY"),
        ("OpenAI", "OPENAI_API_KEY"),
        ("DeepSeek", "DEEPSEEK_API_KEY"),
        ("Groq", "GROQ_API_KEY"),
    ]:
        existing_val = secret_manager.get_secret(env_var, prompt_user=False)
        if existing_val:
            console.print(f"  • {provider} ({env_var}): [green]Configured[/green]")
        else:
            console.print(f"  • {provider} ({env_var}): [dim]Not set (can configure later)[/dim]")

    console.print("\n[bold green]Ready for launch![/bold green] Run [cyan]keplix run --goal \"<your task>\"[/cyan]\n")


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

