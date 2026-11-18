"""Step 1: Environment Detection screen and interactive controls."""

from keplix.cli.wizard.context import EnvironmentInfo, SetupContext
from keplix.cli.wizard.detector import run_environment_detection
from keplix.cli.wizard.ui import (
    CLR_CYAN,
    CLR_DIM,
    CLR_GREEN,
    CLR_PURPLE,
    CLR_RED,
    CLR_YELLOW,
    NAV_BACK,
    Group,
    Panel,
    Table,
    Text,
    WizardCancelledException,
    build_step_title,
    build_wizard_header,
    clear_screen,
    console,
    format_path_display,
    prompt_press_enter,
    prompt_select,
    render_step_title,
    render_wizard_header,
)


def _build_env_panel(info: EnvironmentInfo) -> Panel:
    """Build the structured environment detection results panel."""
    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold", justify="left")
    table.add_column(style="dim", justify="right")

    # A. OS
    os_status = f"[{CLR_GREEN}]✔[/{CLR_GREEN}] Operating system detected"
    table.add_row(f"  {os_status}", f"[{CLR_CYAN}]{info.os_version}[/{CLR_CYAN}]")

    # B. CWD
    cwd_disp = format_path_display(info.cwd)
    cwd_icon = f"[{CLR_GREEN}]✔[/{CLR_GREEN}]" if (info.cwd_readable and info.cwd_writable) else f"[{CLR_RED}]✖[/{CLR_RED}]"
    table.add_row(f"  {cwd_icon} Working directory detected", f"[{CLR_CYAN}]{cwd_disp}[/{CLR_CYAN}]")

    # C. Python
    py_icon = f"[{CLR_GREEN}]✔[/{CLR_GREEN}]" if info.python_supported else f"[{CLR_RED}]✖[/{CLR_RED}]"
    py_text = f"Python {info.python_version}" + ("" if info.python_supported else " [UNSUPPORTED]")
    table.add_row(f"  {py_icon} Python detected", f"[{CLR_CYAN}]{py_text}[/{CLR_CYAN}]")

    # D. Git
    if info.git_available and info.is_git_repo:
        git_label = f"[{CLR_GREEN}]✔[/{CLR_GREEN}] Git repository detected"
        branch_str = f"Branch: {info.git_branch or 'main'}"
        table.add_row(f"  {git_label}", f"[{CLR_CYAN}]{branch_str}[/{CLR_CYAN}]")
    elif info.git_available:
        git_label = f"[{CLR_YELLOW}]⚠[/{CLR_YELLOW}] Git installed (no repo)"
        table.add_row(f"  {git_label}", f"[{CLR_DIM}]Not a git repository[/{CLR_DIM}]")
    else:
        git_label = f"[{CLR_YELLOW}]⚠[/{CLR_YELLOW}] Git not detected"
        table.add_row(f"  {git_label}", f"[{CLR_DIM}]Optional (rollbacks disabled)[/{CLR_DIM}]")

    # E. Docker
    if info.docker_cli_available and info.docker_daemon_running:
        docker_label = f"[{CLR_GREEN}]✔[/{CLR_GREEN}] Docker detected"
        version_str = f"Docker Engine {info.docker_server_version or info.docker_cli_version or 'active'}"
        table.add_row(f"  {docker_label}", f"[{CLR_CYAN}]{version_str}[/{CLR_CYAN}]")
    elif info.docker_cli_available:
        docker_label = f"[{CLR_YELLOW}]⚠[/{CLR_YELLOW}] Docker CLI detected"
        table.add_row(f"  {docker_label}", f"[{CLR_YELLOW}]Daemon not running[/{CLR_YELLOW}]")
    else:
        docker_label = f"[{CLR_YELLOW}]⚠[/{CLR_YELLOW}] Docker not detected"
        table.add_row(f"  {docker_label}", f"[{CLR_DIM}]Optional (local fallback)[/{CLR_DIM}]")

    # F. Keplix
    keplix_label = f"[{CLR_GREEN}]✔[/{CLR_GREEN}] Keplix installation verified"
    table.add_row(f"  {keplix_label}", f"[{CLR_CYAN}]keplix v{info.keplix_version}[/{CLR_CYAN}]")

    # G. Keyring
    if info.keyring_available and info.keyring_usable:
        keyring_label = f"[{CLR_GREEN}]✔[/{CLR_GREEN}] Credential backend detected"
        table.add_row(f"  {keyring_label}", f"[{CLR_CYAN}]{info.keyring_backend}[/{CLR_CYAN}]")
    else:
        keyring_label = f"[{CLR_YELLOW}]⚠[/{CLR_YELLOW}] Credential backend"
        table.add_row(f"  {keyring_label}", f"[{CLR_DIM}Environment / .env fallback[/{CLR_DIM}]")

    # H. Environment Variables
    avail_count = sum(1 for present in info.provider_keys.values() if present)
    if avail_count > 0:
        keys_summary = f"{avail_count} provider keys available"
        key_icon = f"[{CLR_GREEN}]✔[/{CLR_GREEN}]"
    else:
        keys_summary = "None detected (configure in Step 5)"
        key_icon = f"[{CLR_YELLOW}]⚠[/{CLR_YELLOW}]"
    table.add_row(f"  {key_icon} Provider environment keys", f"[{CLR_CYAN}]{keys_summary}[/{CLR_CYAN}]")

    return Panel(
        table,
        border_style=CLR_PURPLE,
        padding=(1, 2),
        expand=False,
    )


def _render_env_panel(info: EnvironmentInfo) -> None:
    """Render the structured environment detection results panel."""
    console.print(_build_env_panel(info))


def run_step1_environment(context: SetupContext) -> str:
    """Execute Step 1 — Environment Detection.

    Inspects environment read-only, displays findings, and offers interaction options:
    - Continue (if required checks pass)
    - Recheck environment
    - Exit

    Returns:
        "continue", "recheck", or "exit".
    """
    while True:
        clear_screen()

        # Run fresh read-only detection
        env_info = run_environment_detection()
        context.env_info = env_info

        # Status summary banner matching the reference screenshot
        if env_info.all_required_passed and not env_info.warnings:
            summary_panel = Panel(
                f"[bold {CLR_GREEN}]✔ Everything looks good.[/bold {CLR_GREEN}]",
                border_style=CLR_GREEN,
                padding=(0, 2),
                expand=False,
            )
        elif env_info.all_required_passed:
            summary_panel = Panel(
                f"[bold {CLR_YELLOW}]⚠ Environment checks passed with warnings.[/bold {CLR_YELLOW}]",
                border_style=CLR_YELLOW,
                padding=(0, 2),
                expand=False,
            )
        else:
            # Fatal error explanation
            err_msg = "\n".join(f"  • {e}" for e in env_info.errors)
            summary_panel = Panel(
                f"[bold {CLR_RED}]✖ Required environment checks failed:[/bold {CLR_RED}]\n{err_msg}",
                border_style=CLR_RED,
                padding=(1, 2),
                expand=False,
            )

        # Build interactive action menu
        options = []
        if env_info.all_required_passed:
            options.append({
                "id": "continue",
                "title": "Continue",
                "description": "Proceed to workspace configuration",
                "badges": ["RECOMMENDED"] if not env_info.warnings else [],
            })
        else:
            options.append({
                "id": "disabled_continue",
                "title": "Cannot Continue (Fix required errors above)",
                "description": "Supported Python >= 3.12 and writable directory are required",
                "badges": ["NOT RECOMMENDED"],
            })

        options.append({
            "id": "recheck",
            "title": "Recheck environment",
            "description": "Rerun all system and workspace checks",
            "badges": [],
        })
        options.append({
            "id": "exit",
            "title": "Exit",
            "description": "Terminate initialization setup",
            "badges": [],
        })

        header_group = Group(
            build_wizard_header(current_step=1, total_steps=context.total_steps, completed_steps=set()),
            build_step_title("⬡", f"STEP 1/{context.total_steps}: ENVIRONMENT DETECTION", "Checking your system and workspace..."),
            _build_env_panel(env_info),
            Text(""),
            summary_panel,
            Text(""),
        )

        choice = prompt_select(
            title=None,
            options=options,
            default_idx=0,
            allow_back=True,
            header_renderable=header_group,
        )

        if choice == "disabled_continue":
            console.print(f"  [bold {CLR_RED}]Cannot continue until required checks pass.[/bold {CLR_RED}]")
            prompt_press_enter("Press Enter to recheck...")
            continue
        elif choice == "recheck":
            continue
        elif choice == "exit":
            raise WizardCancelledException()
        elif choice == NAV_BACK:
            return NAV_BACK
        elif choice == "continue":
            return "continue"
