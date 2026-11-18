"""Step 0: Welcome screen for Keplix CLI First-Run Setup."""

import os
import sys
import time

from rich.live import Live

from keplix.cli.wizard.context import SetupContext
from keplix.cli.wizard.ui import (
    CLR_CYAN,
    CLR_DIM,
    CLR_PURPLE,
    Group,
    Panel,
    Text,
    WizardCancelledException,
    _get_key_non_blocking,
    badge_experimental,
    badge_not_recommended,
    badge_recommended,
    badge_stable,
    build_keplix_brand_banner,
    clear_screen,
    console,
)


def _build_welcome_group() -> Group:
    welcome_panel = Panel(
        f"[bold white]Welcome to Keplix![/bold white]\n\n"
        f"Let's configure your workspace and get your AI\n"
        f"agents ready to work.\n\n"
        f"[dim]This setup should only take a few minutes.[/dim]\n\n"
        f"  {badge_recommended()}   = Preferred choice\n"
        f"  {badge_stable()}        = Production-ready\n"
        f"  {badge_experimental()}  = Early implementation\n"
        f"  {badge_not_recommended()}= Avoid for normal usage\n",
        border_style=CLR_PURPLE,
        padding=(1, 2),
        expand=False,
    )
    prompt_text = Text.from_markup(f"  [dim {CLR_CYAN}]Press Enter to begin setup... (or 'q' to cancel)[/dim {CLR_CYAN}]")
    return Group(
        build_keplix_brand_banner(),
        welcome_panel,
        Text(""),
        prompt_text,
    )


def run_step0_welcome(context: SetupContext) -> bool:
    """Execute Step 0 — Welcome screen.

    Displays product mission, setup explanation, and badge glossary.
    Performs NO filesystem changes, configuration changes, or subprocess calls.

    Returns:
        True to advance to Step 1.
    """
    is_interactive = sys.stdin.isatty() and not os.getenv("KEPLIX_TEST_NON_INTERACTIVE")
    if not is_interactive:
        clear_screen()
        console.print(_build_welcome_group())
        return True

    last_size = console.size
    with Live(_build_welcome_group(), console=console, screen=True, auto_refresh=False) as live:
        while True:
            current_size = console.size
            if current_size != last_size:
                last_size = current_size
                live.update(_build_welcome_group(), refresh=True)

            try:
                key = _get_key_non_blocking()
            except KeyboardInterrupt:
                raise WizardCancelledException()

            if key is None:
                time.sleep(0.04)
                continue

            if key in ("ENTER", "\r", "\n", "SPACE"):
                return True
            elif key in ("q", "Q"):
                raise WizardCancelledException()
