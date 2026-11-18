"""Step 2: Workspace Configuration screen and nested scenarios (Options 1, 2, 3)."""

import os
from pathlib import Path
import re
from typing import Any, Optional

from keplix.cli.wizard.context import (
    SetupContext,
    WorkspaceInspectionResult,
    WorkspaceState,
)
from keplix.cli.wizard.inspector import WorkspaceInspector
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
    Tree,
    WizardCancelledException,
    build_step_title,
    build_wizard_header,
    clear_screen,
    console,
    format_path_display,
    prompt_press_enter,
    prompt_select,
    prompt_text_input,
    render_step_title,
    render_wizard_header,
)

WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
}


def validate_project_name(name: str) -> tuple[bool, str]:
    """Validate project folder name for filesystem and cross-platform compatibility."""
    if not name or not name.strip():
        return False, "Project name cannot be empty."

    # Trailing dots or spaces (invalid on Windows and causes issues cross-platform)
    if name.endswith(".") or name.endswith(" ") or name.startswith(" "):
        return False, "Project name cannot start or end with a dot or space."

    cleaned = name.strip()

    if "/" in cleaned or "\\" in cleaned:
        return False, "Project name cannot contain path separators ('/' or '\\')."

    if cleaned in (".", "..") or ".." in cleaned:
        return False, "Project name cannot contain relative path traversal ('.' or '..')."

    # Invalid filesystem characters
    if re.search(r'[<>:"/\\|?*]', cleaned):
        return False, 'Project name contains invalid characters (< > : " / \\ | ? *).'

    # Windows reserved filenames check (case-insensitive, even with extension)
    stem = cleaned.split(".")[0].upper()
    if stem in WINDOWS_RESERVED_NAMES:
        return False, f"'{cleaned}' is a reserved system filename on Windows."

    if len(cleaned) > 255:
        return False, "Project name exceeds maximum length of 255 characters."

    return True, ""


def resolve_candidate_path(input_str: str) -> tuple[Optional[Path], Optional[str]]:
    """Expand ~, resolve canonical path, and validate existence and permissions."""
    raw = input_str.strip()
    if not raw:
        return None, "Path cannot be empty."

    try:
        expanded = Path(raw).expanduser()
        resolved = expanded.resolve()

        if not resolved.exists():
            return None, f"Directory does not exist: {resolved}"

        if not resolved.is_dir():
            return None, f"Path is a file, not a directory: {resolved}"

        if not os.access(resolved, os.R_OK):
            return None, f"Directory is not readable: {resolved}"

        if not os.access(resolved, os.W_OK):
            return None, f"Directory is not writable: {resolved}"

        return resolved, None
    except Exception as err:
        return None, f"Invalid path syntax: {err}"


def _sanitize_toml_text(raw_text: str) -> str:
    """Mask any secret-like configuration values for the review display."""
    lines = raw_text.splitlines()
    sanitized: list[str] = []
    for line in lines:
        if re.search(r'(api[_-]?key|secret|password|token)\s*=', line, re.IGNORECASE):
            parts = line.split("=", 1)
            sanitized.append(f"{parts[0]}= \"[MASKED]\"")
        else:
            sanitized.append(line)
    return "\n".join(sanitized)


# ---------------------------------------------------------------------------
# Workspace Scenario Handlers
# ---------------------------------------------------------------------------

def handle_existing_workspace(
    context: SetupContext,
    target_path: Path,
    inspection: WorkspaceInspectionResult,
) -> bool:
    """Handle Scenario B: Both keplix.toml and .keplix/ exist."""
    while True:
        clear_screen()
        disp_path = format_path_display(target_path)
        existing_panel = Panel(
            f"[bold {CLR_YELLOW}]Existing Keplix workspace detected![/bold {CLR_YELLOW}]\n\n"
            f"Directory: [{CLR_CYAN}]{disp_path}[/{CLR_CYAN}]\n"
            f"Found valid [bold]keplix.toml[/bold] and runtime store at [bold].keplix/[/bold]",
            border_style=CLR_YELLOW,
            padding=(1, 2),
            expand=False,
        )
        header_group = Group(
            build_wizard_header(current_step=2, total_steps=context.total_steps, completed_steps={1}),
            build_step_title("⬡", f"STEP 2/{context.total_steps}: WORKSPACE CONFIGURATION"),
            existing_panel,
            Text(""),
        )

        options = [
            {
                "id": "continue",
                "title": "Continue with existing configuration",
                "description": "Preserve all existing settings and proceed with setup",
                "badges": ["RECOMMENDED", "STABLE"],
            },
            {
                "id": "review",
                "title": "Review configuration",
                "description": "Inspect existing TOML configuration settings (secrets masked)",
                "badges": [],
            },
            {
                "id": "reconfigure",
                "title": "Reconfigure workspace",
                "description": "Keep existing settings as defaults but update in later stages",
                "badges": [],
            },
            {
                "id": "cancel",
                "title": "Cancel initialization",
                "description": "Exit setup without modifying workspace",
                "badges": [],
            },
        ]

        choice = prompt_select(None, options, default_idx=0, allow_back=True, header_renderable=header_group)

        if choice == "cancel":
            raise WizardCancelledException()
        elif choice == NAV_BACK:
            return False
        elif choice == "continue":
            context.config_action = "continue"
            return True
        elif choice == "reconfigure":
            context.config_action = "reconfigure"
            return True
        elif choice == "review":
            # Display sanitized configuration
            clear_screen()
            masked_text = _sanitize_toml_text(inspection.raw_config_text or "# Empty configuration")
            review_header = Group(
                build_wizard_header(current_step=2, total_steps=context.total_steps, completed_steps={1}),
                Text.from_markup(f"  [bold {CLR_CYAN}]Configuration Review: {disp_path}/keplix.toml[/bold {CLR_CYAN}]\n"),
                Panel(masked_text, border_style=CLR_PURPLE, expand=False),
                Text(""),
            )

            review_options = [
                {"id": "continue", "title": "Continue with this configuration", "badges": ["RECOMMENDED"]},
                {"id": "reconfigure", "title": "Reconfigure workspace in later steps", "badges": []},
                {"id": "back", "title": "Go back", "badges": []},
            ]
            rev_choice = prompt_select(None, review_options, default_idx=0, allow_back=True, header_renderable=review_header)
            if rev_choice == "continue":
                context.config_action = "continue"
                return True
            elif rev_choice == "reconfigure":
                context.config_action = "reconfigure"
                return True
            # If back, loops to existing workspace screen


def handle_partial_runtime(
    context: SetupContext,
    target_path: Path,
    inspection: WorkspaceInspectionResult,
) -> bool:
    """Handle Scenario D: .keplix/ exists but keplix.toml is missing."""
    while True:
        clear_screen()
        disp_path = format_path_display(target_path)
        partial_panel = Panel(
            f"[bold {CLR_YELLOW}]Existing runtime directory detected,[/bold {CLR_YELLOW}]\n"
            f"[dim]but keplix.toml is missing.[/dim]\n\n"
            f"Directory: [{CLR_CYAN}]{disp_path}/.keplix[/{CLR_CYAN}]",
            border_style=CLR_YELLOW,
            padding=(1, 2),
            expand=False,
        )
        header_group = Group(
            build_wizard_header(current_step=2, total_steps=context.total_steps, completed_steps={1}),
            build_step_title("⬡", f"STEP 2/{context.total_steps}: WORKSPACE CONFIGURATION"),
            partial_panel,
            Text(""),
        )

        options = [
            {
                "id": "preserve",
                "title": "Preserve runtime data and continue",
                "description": "Keep existing checkpoints and database, generate new configuration later",
                "badges": ["RECOMMENDED"],
            },
            {
                "id": "inspect",
                "title": "Inspect runtime directory",
                "description": "View subdirectories, files, and sizes (no sensitive contents exposed)",
                "badges": [],
            },
            {
                "id": "cancel",
                "title": "Cancel initialization",
                "description": "Exit setup without modifying anything",
                "badges": [],
            },
        ]

        choice = prompt_select(None, options, default_idx=0, allow_back=True, header_renderable=header_group)

        if choice == "cancel":
            raise WizardCancelledException()
        elif choice == NAV_BACK:
            return False
        elif choice == "preserve":
            context.config_action = "preserve"
            context.is_partial_workspace = True
            return True
        elif choice == "inspect":
            # Directory structure inspection
            clear_screen()
            render_wizard_header(current_step=2, total_steps=context.total_steps, completed_steps={1})
            runtime_dir = target_path / ".keplix"

            tree = Tree(f"[bold {CLR_CYAN}].keplix/[/bold {CLR_CYAN}]")
            try:
                for item in sorted(runtime_dir.rglob("*")):
                    rel = item.relative_to(runtime_dir)
                    if item.is_file():
                        size_kb = item.stat().st_size / 1024.0
                        tree.add(f"{rel} [dim]({size_kb:.1f} KB)[/dim]")
                    elif item.is_dir():
                        tree.add(f"[bold]{rel}/[/bold]")
            except Exception as e:
                tree.add(f"[red]Error inspecting directory: {e}[/red]")

            console.print(Panel(tree, title="Runtime Directory Inspection", border_style=CLR_PURPLE, expand=False))
            console.print()
            prompt_press_enter("Press Enter to return...")


def handle_invalid_configuration(
    context: SetupContext,
    target_path: Path,
    inspection: WorkspaceInspectionResult,
) -> bool:
    """Handle Scenario E: Invalid keplix.toml."""
    while True:
        clear_screen()
        disp_path = format_path_display(target_path)
        err_list = "\n".join(f"  • {e}" for e in inspection.validation_errors)

        invalid_panel = Panel(
            f"[bold {CLR_RED}]Invalid keplix.toml detected![/bold {CLR_RED}]\n\n"
            f"Directory: [{CLR_CYAN}]{disp_path}[/{CLR_CYAN}]\n\n"
            f"[bold]Validation Errors:[/bold]\n{err_list}\n\n"
            f"[dim]The original configuration file has been preserved intact.[/dim]",
            border_style=CLR_RED,
            padding=(1, 2),
            expand=False,
        )
        header_group = Group(
            build_wizard_header(current_step=2, total_steps=context.total_steps, completed_steps={1}),
            build_step_title("⬡", f"STEP 2/{context.total_steps}: WORKSPACE CONFIGURATION"),
            invalid_panel,
            Text(""),
        )

        options = [
            {
                "id": "inspect",
                "title": "Inspect validation errors and raw file",
                "description": "View exact parsing breakdown to fix manually",
                "badges": [],
            },
            {
                "id": "exit",
                "title": "Exit and fix manually",
                "description": "Exit initialization wizard so you can correct keplix.toml",
                "badges": ["RECOMMENDED"],
            },
            {
                "id": "back",
                "title": "Go back to workspace selection",
                "description": "Select a different directory instead",
                "badges": [],
            },
        ]

        choice = prompt_select(None, options, default_idx=1, allow_back=True, header_renderable=header_group)

        if choice == "exit":
            raise WizardCancelledException()
        elif choice in ("back", NAV_BACK):
            return False  # Signals to caller to return to main Step 2
        elif choice == "inspect":
            clear_screen()
            render_wizard_header(current_step=2, total_steps=context.total_steps, completed_steps={1})
            console.print(f"  [bold {CLR_RED}]Raw keplix.toml content:[/bold {CLR_RED}]\n")
            console.print(Panel(inspection.raw_config_text or "# Empty", border_style=CLR_RED, expand=False))
            console.print(f"\n  [bold {CLR_RED}]Validation details:[/bold {CLR_RED}]\n")
            for err in inspection.validation_errors:
                console.print(f"  • [red]{err}[/red]")
            console.print()
            prompt_press_enter("Press Enter to return...")


def process_inspected_workspace(
    context: SetupContext,
    target_path: Path,
    selection_method: str,
    is_new: bool = False,
) -> bool:
    """Process an inspected directory through all 5 scenarios (A-E).

    Returns:
        True if workspace accepted and ready for Step 3, False if user chose to go back.
    """
    inspection = WorkspaceInspector.inspect(target_path, is_newly_created=is_new)
    context.set_workspace_path(target_path, method=selection_method, is_new=is_new)
    context.inspection = inspection

    state = inspection.state

    # Scenario A: Fresh Workspace
    if state == WorkspaceState.FRESH_WORKSPACE:
        context.config_action = "fresh"
        return True

    # Scenario B: Existing Workspace (TOML and runtime present)
    elif state == WorkspaceState.EXISTING_WORKSPACE:
        return handle_existing_workspace(context, target_path, inspection)

    # Scenario C: Existing Configuration (TOML present, runtime missing)
    elif state == WorkspaceState.EXISTING_CONFIGURATION:
        context.config_action = "continue"
        context.is_partial_workspace = True
        return True

    # Scenario D: Partial Runtime (.keplix/ present, TOML missing)
    elif state == WorkspaceState.PARTIAL_RUNTIME:
        return handle_partial_runtime(context, target_path, inspection)

    # Scenario E: Invalid Configuration
    elif state == WorkspaceState.INVALID_CONFIGURATION:
        return handle_invalid_configuration(context, target_path, inspection)

    return True


# ---------------------------------------------------------------------------
# Main Step 2 Flows: Option 1, Option 2, Option 3
# ---------------------------------------------------------------------------

def run_option1_current_directory(context: SetupContext) -> bool:
    """Option 1: Use current working directory."""
    cwd = Path.cwd().resolve()
    return process_inspected_workspace(context, cwd, selection_method="current", is_new=False)


def run_option2_choose_directory(context: SetupContext) -> bool:
    """Option 2: Choose another existing project directory."""
    while True:
        clear_screen()
        render_wizard_header(current_step=2, total_steps=context.total_steps, completed_steps={1})
        render_step_title("⬡", f"STEP 2/{context.total_steps}: WORKSPACE CONFIGURATION", "Specify an existing project directory")

        console.print("  [dim]Enter the path to your project (supports ~, relative, and absolute paths):[/dim]\n")
        path_input = prompt_text_input("Project directory path", allow_back=True)

        if path_input == NAV_BACK:
            return False

        target_path, err_msg = resolve_candidate_path(path_input)
        if err_msg or target_path is None:
            console.print(f"\n  [bold {CLR_RED}]✖ {err_msg}[/bold {CLR_RED}]\n")
            prompt_press_enter("Press Enter to try again...")
            continue

        # Inspect candidate directory and display summary
        temp_inspection = WorkspaceInspector.inspect(target_path)
        disp_path = format_path_display(target_path)

        clear_screen()
        summary_text = (
            f"[bold]Selected workspace:[/bold]\n\n"
            f"[{CLR_CYAN}]{disp_path}[/{CLR_CYAN}]\n\n"
            f"[{CLR_GREEN}]✔[/{CLR_GREEN}] Directory exists\n"
            f"[{CLR_GREEN}]✔[/{CLR_GREEN}] Read/write permissions available\n"
        )
        if temp_inspection.has_git:
            summary_text += f"[{CLR_GREEN}]✔[/{CLR_GREEN}] Git repository detected ({temp_inspection.git_branch or 'main'})\n"
        else:
            summary_text += f"[{CLR_YELLOW}]⚠[/{CLR_YELLOW}] No Git repository detected\n"

        if temp_inspection.state == WorkspaceState.FRESH_WORKSPACE:
            summary_text += f"[{CLR_GREEN}]✔[/{CLR_GREEN}] No existing Keplix configuration\n"
        elif temp_inspection.state == WorkspaceState.EXISTING_WORKSPACE:
            summary_text += f"[{CLR_CYAN}]✔[/{CLR_CYAN}] Existing Keplix workspace detected\n"
        elif temp_inspection.state == WorkspaceState.INVALID_CONFIGURATION:
            summary_text += f"[{CLR_RED}]✖[/{CLR_RED}] Invalid keplix.toml detected\n"
        elif temp_inspection.state == WorkspaceState.PARTIAL_RUNTIME:
            summary_text += f"[{CLR_YELLOW}]⚠[/{CLR_YELLOW}] Orphaned runtime directory detected\n"

        summary_panel = Panel(summary_text, border_style=CLR_PURPLE, padding=(1, 2), expand=False)
        confirm_header = Group(
            build_wizard_header(current_step=2, total_steps=context.total_steps, completed_steps={1}),
            build_step_title("⬡", f"STEP 2/{context.total_steps}: WORKSPACE CONFIGURATION"),
            summary_panel,
            Text(""),
        )

        confirm_options = [
            {"id": "continue", "title": "Yes, continue", "badges": ["RECOMMENDED"]},
            {"id": "rechoose", "title": "Choose another directory", "badges": []},
            {"id": "back", "title": "Go back", "badges": []},
        ]

        conf_choice = prompt_select(None, confirm_options, default_idx=0, allow_back=True, header_renderable=confirm_header)

        if conf_choice == "continue":
            # Run full scenario processing on target_path
            return process_inspected_workspace(context, target_path, selection_method="choose", is_new=False)
        elif conf_choice == "rechoose":
            continue
        elif conf_choice in ("back", NAV_BACK):
            return False


def run_option3_create_directory(context: SetupContext) -> bool:
    """Option 3: Create a new project directory."""
    default_parent = Path.cwd().resolve()
    parent_path = default_parent

    while True:
        clear_screen()
        render_wizard_header(current_step=2, total_steps=context.total_steps, completed_steps={1})
        render_step_title("⬡", f"STEP 2/{context.total_steps}: WORKSPACE CONFIGURATION", "Create a new project workspace")

        # 1. Ask for parent directory
        parent_disp = format_path_display(parent_path)
        console.print(f"  [bold]Parent directory:[/bold] [{CLR_CYAN}]{parent_disp}[/{CLR_CYAN}]")
        console.print("  [dim]Press Enter to use this parent, or type a new path:[/dim]")

        new_parent_input = prompt_text_input("Parent directory", default=str(parent_path), allow_back=True)
        if new_parent_input == NAV_BACK:
            return False

        validated_parent, parent_err = resolve_candidate_path(new_parent_input)
        if parent_err or validated_parent is None:
            console.print(f"\n  [bold {CLR_RED}]✖ {parent_err}[/bold {CLR_RED}]\n")
            prompt_press_enter("Press Enter to try again...")
            continue

        parent_path = validated_parent

        # 2. Ask for project directory name
        console.print("\n  [bold]Project directory name:[/bold]")
        console.print("  [dim]Enter folder name (e.g. weather-dashboard):[/dim]")

        name_input = prompt_text_input(
            "Project name",
            validator=validate_project_name,
            allow_back=True,
        )
        if name_input == NAV_BACK:
            continue

        final_location = parent_path / name_input
        final_disp = format_path_display(final_location)

        clear_screen()

        # Scenario A: Destination does NOT exist
        if not final_location.exists():
            confirm_box = Panel(
                f"[bold]Create workspace?[/bold]\n\n"
                f"[{CLR_CYAN}]{final_disp}[/{CLR_CYAN}]\n\n"
                f"Parent: {format_path_display(parent_path)}\n"
                f"Project: {name_input}",
                border_style=CLR_PURPLE,
                padding=(1, 2),
                expand=False,
            )
            create_header = Group(
                build_wizard_header(current_step=2, total_steps=context.total_steps, completed_steps={1}),
                build_step_title("⬡", f"STEP 2/{context.total_steps}: WORKSPACE CONFIGURATION", "Create a new project workspace"),
                confirm_box,
                Text(""),
            )

            create_options = [
                {"id": "create", "title": "Create and continue", "badges": ["RECOMMENDED"]},
                {"id": "change_name", "title": "Change project name", "badges": []},
                {"id": "change_parent", "title": "Change parent directory", "badges": []},
                {"id": "back", "title": "Go back", "badges": []},
            ]

            choice = prompt_select(None, create_options, default_idx=0, allow_back=True, header_renderable=create_header)

            if choice == "create":
                # Safe creation with exist_ok=False
                try:
                    final_location.mkdir(parents=False, exist_ok=False)
                    return process_inspected_workspace(
                        context,
                        final_location,
                        selection_method="create",
                        is_new=True,
                    )
                except Exception as err:
                    console.print(f"\n  [bold {CLR_RED}]Failed to create directory: {err}[/bold {CLR_RED}]\n")
                    prompt_press_enter("Press Enter to retry...")
                    continue
            elif choice == "change_name":
                continue
            elif choice == "change_parent":
                continue
            elif choice in ("back", NAV_BACK):
                return False

        # Scenario B: Destination ALREADY exists
        else:
            exist_box = Panel(
                f"[bold {CLR_YELLOW}]Directory already exists![/bold {CLR_YELLOW}]\n\n"
                f"[{CLR_CYAN}]{final_disp}[/{CLR_CYAN}]\n\n"
                f"[dim]The destination directory already exists on disk.[/dim]",
                border_style=CLR_YELLOW,
                padding=(1, 2),
                expand=False,
            )
            exist_header = Group(
                build_wizard_header(current_step=2, total_steps=context.total_steps, completed_steps={1}),
                build_step_title("⬡", f"STEP 2/{context.total_steps}: WORKSPACE CONFIGURATION", "Create a new project workspace"),
                exist_box,
                Text(""),
            )

            exist_options = [
                {"id": "use_existing", "title": "Use this existing directory", "badges": ["RECOMMENDED"]},
                {"id": "change_name", "title": "Choose another project name", "badges": []},
                {"id": "change_parent", "title": "Choose another parent directory", "badges": []},
                {"id": "back", "title": "Go back", "badges": []},
            ]

            choice = prompt_select(None, exist_options, default_idx=0, allow_back=True, header_renderable=exist_header)

            if choice == "use_existing":
                # Use existing directory without overwriting contents
                return process_inspected_workspace(
                    context,
                    final_location,
                    selection_method="create",
                    is_new=False,
                )
            elif choice == "change_name":
                continue
            elif choice == "change_parent":
                continue
            elif choice in ("back", NAV_BACK):
                return False


def run_step2_workspace(context: SetupContext) -> bool:
    """Execute Step 2 — Workspace Configuration.

    Displays main menu and dispatches to Option 1, 2, or 3.
    Supports Esc / Go Back to return to Step 1.
    """
    while True:
        clear_screen()
        cwd = Path.cwd().resolve()
        cwd_disp = format_path_display(cwd)

        header_group = Group(
            build_wizard_header(current_step=2, total_steps=context.total_steps, completed_steps={1}),
            build_step_title("⬡", f"STEP 2/{context.total_steps}: WORKSPACE CONFIGURATION"),
            Text.from_markup("  [bold]Where should Keplix operate?[/bold]\n"),
            Text.from_markup("  [dim]Current directory:[/dim]"),
            Text.from_markup(f"  [{CLR_CYAN}]{cwd_disp}[/{CLR_CYAN}]\n"),
        )

        options = [
            {
                "id": "current",
                "title": "Use current directory",
                "description": "Initialize Keplix in this directory.",
                "badges": ["RECOMMENDED", "STABLE"],
            },
            {
                "id": "choose",
                "title": "Choose another directory",
                "description": "Specify a different existing project.",
                "badges": [],
            },
            {
                "id": "create",
                "title": "Create a new project directory",
                "description": "Initialize a new workspace in a new folder.",
                "badges": [],
            },
        ]

        choice = prompt_select(None, options, default_idx=0, allow_back=True, header_renderable=header_group)

        if choice == NAV_BACK:
            return False  # Go back to Step 1
        elif choice == "current":
            if run_option1_current_directory(context):
                return True
        elif choice == "choose":
            if run_option2_choose_directory(context):
                return True
        elif choice == "create":
            if run_option3_create_directory(context):
                return True
