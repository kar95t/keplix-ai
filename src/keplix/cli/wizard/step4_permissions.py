"""Step 4: Capabilities and permissions configuration for Keplix CLI First-Run Setup."""

from typing import Optional, Union

from keplix.cli.wizard.context import SetupContext
from keplix.cli.wizard.ui import (
    CLR_CYAN,
    CLR_PURPLE,
    NAV_BACK,
    Group,
    Text,
    build_step_pill_header,
    clear_screen,
    console,
    prompt_permission_action,
    prompt_select,
    render_step_pill_header,
)
from keplix.config.settings import (
    ExecutionPermissions,
    ExternalActionPermissions,
    FilesystemPermissions,
    NetworkMode,
    NetworkPermissions,
    PermissionAction,
    PermissionConfig,
    PermissionProfile,
    resolve_profile_permissions,
)


def _customize_permissions(baseline: PermissionConfig) -> Optional[PermissionConfig]:
    """Sub-flow for configuring custom individual permissions with explicit modal sub-menus."""
    custom_cfg = PermissionConfig(
        profile=PermissionProfile.CUSTOM,
        filesystem=FilesystemPermissions(
            read_workspace=baseline.filesystem.read_workspace,
            create_files=baseline.filesystem.create_files,
            modify_files=baseline.filesystem.modify_files,
            delete_files=baseline.filesystem.delete_files,
            access_outside_workspace=baseline.filesystem.access_outside_workspace,
        ),
        execution=ExecutionPermissions(
            terminal_commands=baseline.execution.terminal_commands,
            run_tests=baseline.execution.run_tests,
            install_dependencies=baseline.execution.install_dependencies,
            git_commit=baseline.execution.git_commit,
            git_push=baseline.execution.git_push,
        ),
        network=NetworkPermissions(
            mode=baseline.network.mode,
            allowed_domains=list(baseline.network.allowed_domains),
        ),
        external_actions=ExternalActionPermissions(
            deployment=baseline.external_actions.deployment,
            publishing=baseline.external_actions.publishing,
            sending_emails=baseline.external_actions.sending_emails,
            destructive_actions=baseline.external_actions.destructive_actions,
        ),
    )

    current_cursor_idx = 0

    while True:
        clear_screen()
        header_group = Group(
            build_step_pill_header(
                current_step=4,
                total_steps=9,
                step_name="Custom Permissions",
                left_title="keplix init",
            ),
            Text.from_markup("  [bold white]Customize Permission Overrides[/bold white]"),
            Text.from_markup("  [dim]Select any permission to configure its enforcement level (allow, approval, sandbox, deny):[/dim]\n"),
        )

        custom_options = [
            {
                "id": "confirm",
                "title": "Save & Confirm Custom Profile",
                "description": "Accept custom configuration and proceed to the next stage.",
                "badges": ["RECOMMENDED"],
            },
            {
                "id": "terminal_commands",
                "title": f"Terminal Commands: [{custom_cfg.execution.terminal_commands.value}]",
                "description": "Allowed: allow, approval, sandbox, deny.",
                "badges": [],
            },
            {
                "id": "run_tests",
                "title": f"Run Tests: [{custom_cfg.execution.run_tests.value}]",
                "description": "Allowed: allow, approval, sandbox, deny.",
                "badges": [],
            },
            {
                "id": "install_dependencies",
                "title": f"Install Dependencies: [{custom_cfg.execution.install_dependencies.value}]",
                "description": "Allowed: allow, approval, sandbox, deny.",
                "badges": [],
            },
            {
                "id": "git_commit",
                "title": f"Git Commit: [{custom_cfg.execution.git_commit.value}]",
                "description": "Allowed: allow, approval, sandbox, deny.",
                "badges": [],
            },
            {
                "id": "git_push",
                "title": f"Git Push: [{custom_cfg.execution.git_push.value}]",
                "description": "Allowed: allow, approval, sandbox, deny.",
                "badges": [],
            },
            {
                "id": "create_files",
                "title": f"Create Files: [{custom_cfg.filesystem.create_files.value}]",
                "description": "Allowed: allow, approval, sandbox, deny.",
                "badges": [],
            },
            {
                "id": "modify_files",
                "title": f"Modify Files: [{custom_cfg.filesystem.modify_files.value}]",
                "description": "Allowed: allow, approval, sandbox, deny.",
                "badges": [],
            },
            {
                "id": "delete_files",
                "title": f"Delete Files: [{custom_cfg.filesystem.delete_files.value}]",
                "description": "Allowed: allow, approval, sandbox, deny.",
                "badges": [],
            },
            {
                "id": "access_outside_workspace",
                "title": f"Access Outside Workspace: [{custom_cfg.filesystem.access_outside_workspace.value}]",
                "description": "Allowed: allow, approval, sandbox, deny.",
                "badges": [],
            },
            {
                "id": "network_mode",
                "title": f"Network Mode: [{custom_cfg.network.mode.value}]",
                "description": "Allowed: allowlist, disabled, unrestricted.",
                "badges": [],
            },
            {
                "id": "deployment",
                "title": f"Deployment: [{custom_cfg.external_actions.deployment.value}]",
                "description": "Allowed: allow, approval, sandbox, deny.",
                "badges": [],
            },
            {
                "id": "publishing",
                "title": f"Publishing: [{custom_cfg.external_actions.publishing.value}]",
                "description": "Allowed: allow, approval, sandbox, deny.",
                "badges": [],
            },
            {
                "id": "sending_emails",
                "title": f"Sending Emails: [{custom_cfg.external_actions.sending_emails.value}]",
                "description": "Allowed: allow, approval, sandbox, deny.",
                "badges": [],
            },
            {
                "id": "destructive_actions",
                "title": f"Destructive Actions: [{custom_cfg.external_actions.destructive_actions.value}]",
                "description": "Allowed: allow, approval, sandbox, deny.",
                "badges": [],
            },
        ]

        choice = prompt_select(
            title=None,
            options=custom_options,
            default_idx=current_cursor_idx,
            allow_back=True,
            header_renderable=header_group,
        )

        if choice == NAV_BACK:
            # User pressed Esc -> return to Step 4 profile selection
            return None

        if choice == "confirm":
            return custom_cfg

        # Map choice to its corresponding option index so cursor stays put
        for idx, opt in enumerate(custom_options):
            if opt["id"] == choice:
                current_cursor_idx = idx
                break

        # Handle modal permission selection
        if choice == "terminal_commands":
            val = prompt_permission_action("Terminal Commands", custom_cfg.execution.terminal_commands.value)
            custom_cfg.execution.terminal_commands = PermissionAction(val)
        elif choice == "run_tests":
            val = prompt_permission_action("Run Tests", custom_cfg.execution.run_tests.value)
            custom_cfg.execution.run_tests = PermissionAction(val)
        elif choice == "install_dependencies":
            val = prompt_permission_action("Install Dependencies", custom_cfg.execution.install_dependencies.value)
            custom_cfg.execution.install_dependencies = PermissionAction(val)
        elif choice == "git_commit":
            val = prompt_permission_action("Git Commit", custom_cfg.execution.git_commit.value)
            custom_cfg.execution.git_commit = PermissionAction(val)
        elif choice == "git_push":
            val = prompt_permission_action("Git Push", custom_cfg.execution.git_push.value)
            custom_cfg.execution.git_push = PermissionAction(val)
        elif choice == "create_files":
            val = prompt_permission_action("Create Files", custom_cfg.filesystem.create_files.value)
            custom_cfg.filesystem.create_files = PermissionAction(val)
        elif choice == "modify_files":
            val = prompt_permission_action("Modify Files", custom_cfg.filesystem.modify_files.value)
            custom_cfg.filesystem.modify_files = PermissionAction(val)
        elif choice == "delete_files":
            val = prompt_permission_action("Delete Files", custom_cfg.filesystem.delete_files.value)
            custom_cfg.filesystem.delete_files = PermissionAction(val)
        elif choice == "access_outside_workspace":
            val = prompt_permission_action("Access Outside Workspace", custom_cfg.filesystem.access_outside_workspace.value)
            custom_cfg.filesystem.access_outside_workspace = PermissionAction(val)
        elif choice == "network_mode":
            val = prompt_permission_action(
                "Network Mode",
                custom_cfg.network.mode.value,
                allowed_values=["allowlist", "disabled", "unrestricted"],
            )
            custom_cfg.network.mode = NetworkMode(val)
        elif choice == "deployment":
            val = prompt_permission_action("Deployment", custom_cfg.external_actions.deployment.value)
            custom_cfg.external_actions.deployment = PermissionAction(val)
        elif choice == "publishing":
            val = prompt_permission_action("Publishing", custom_cfg.external_actions.publishing.value)
            custom_cfg.external_actions.publishing = PermissionAction(val)
        elif choice == "sending_emails":
            val = prompt_permission_action("Sending Emails", custom_cfg.external_actions.sending_emails.value)
            custom_cfg.external_actions.sending_emails = PermissionAction(val)
        elif choice == "destructive_actions":
            val = prompt_permission_action("Destructive Actions", custom_cfg.external_actions.destructive_actions.value)
            custom_cfg.external_actions.destructive_actions = PermissionAction(val)


def run_step4_permissions(context: SetupContext) -> bool:
    """Execute Step 4 — Capabilities and Permissions Configuration.

    Allows user to select a permission profile (Balanced, Restricted, Autonomous, or Custom).

    Args:
        context: Shared in-memory SetupContext holding wizard state.

    Returns:
        True to advance to Step 5.
        False to navigate back to Step 3.
    """
    while True:
        clear_screen()
        header_group = Group(
            build_step_pill_header(
                current_step=4,
                total_steps=context.total_steps,
                step_name="Permissions",
                left_title="Setup Wizard (4/9)",
            ),
            Text.from_markup(f"  [bold {CLR_PURPLE}]Configure Capabilities & Permissions[/bold {CLR_PURPLE}]"),
            Text.from_markup("  [dim]Choose what Keplix agents can access and which actions require your approval.[/dim]\n"),
            Text.from_markup("  [bold white]Permission profile[/bold white]\n"),
        )

        # 4 profile cards matching Image 2
        profile_options = [
            {
                "id": "balanced",
                "title": "Balanced",
                "description": "Allow normal project work while requiring approval for sensitive external actions.",
                "badges": ["RECOMMENDED"],
            },
            {
                "id": "restricted",
                "title": "Restricted",
                "description": "Read-only access by default. Require approval for modifications and external actions.",
                "badges": [],
            },
            {
                "id": "autonomous",
                "title": "Autonomous",
                "description": "Allow a broader set of actions within configured sandbox boundaries. Sensitive actions still require approval.",
                "badges": [],
            },
            {
                "id": "custom",
                "title": "Custom",
                "description": "Configure individual permissions manually.",
                "badges": [],
            },
        ]

        # Determine default index based on existing context
        default_idx = 0
        if context.permissions:
            if context.permissions.profile == PermissionProfile.RESTRICTED:
                default_idx = 1
            elif context.permissions.profile == PermissionProfile.AUTONOMOUS:
                default_idx = 2
            elif context.permissions.profile == PermissionProfile.CUSTOM:
                default_idx = 3

        choice = prompt_select(
            title=None,
            options=profile_options,
            default_idx=default_idx,
            allow_back=True,
            header_renderable=header_group,
        )

        if choice == NAV_BACK:
            return False

        if choice in ("balanced", "restricted", "autonomous"):
            profile_enum = PermissionProfile(choice)
            context.permissions = resolve_profile_permissions(profile_enum)
            return True

        elif choice == "custom":
            baseline = resolve_profile_permissions(PermissionProfile.BALANCED)
            custom_cfg = _customize_permissions(baseline)
            if custom_cfg is None:
                # User pressed Esc from custom menu -> stay on profile selection
                continue
            context.permissions = custom_cfg
            return True
