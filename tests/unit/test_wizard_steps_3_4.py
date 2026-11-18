"""Unit tests for Keplix CLI First-Run Setup Steps 3 & 4 (Domains and Permissions)."""

import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from keplix.cli.wizard.context import SetupContext, WorkspaceInspectionResult, WorkspaceState
from keplix.cli.wizard.controller import WizardController
from keplix.cli.wizard.step3_domains import DOMAIN_PACKS, run_step3_domains
from keplix.cli.wizard.step4_permissions import run_step4_permissions
from keplix.cli.wizard.ui import NAV_BACK, prompt_multi_select, prompt_two_column_domains
from keplix.config.settings import (
    DomainConfig,
    DomainMode,
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


class TestDomainAndPermissionModels(unittest.TestCase):
    """Test Pydantic schemas and profile resolvers."""

    def test_domain_config_defaults(self) -> None:
        cfg = DomainConfig()
        self.assertEqual(cfg.mode, DomainMode.AUTO)
        self.assertEqual(cfg.enabled, [])

    def test_domain_config_specialized(self) -> None:
        cfg = DomainConfig(mode=DomainMode.SPECIALIZED, enabled=["software", "marketing"])
        self.assertEqual(cfg.mode, DomainMode.SPECIALIZED)
        self.assertEqual(cfg.enabled, ["software", "marketing"])

    def test_resolve_balanced_profile(self) -> None:
        cfg = resolve_profile_permissions(PermissionProfile.BALANCED)
        self.assertEqual(cfg.profile, PermissionProfile.BALANCED)
        self.assertEqual(cfg.filesystem.read_workspace, PermissionAction.ALLOW)
        self.assertEqual(cfg.filesystem.create_files, PermissionAction.ALLOW)
        self.assertEqual(cfg.filesystem.modify_files, PermissionAction.ALLOW)
        self.assertEqual(cfg.filesystem.delete_files, PermissionAction.APPROVAL)
        self.assertEqual(cfg.filesystem.access_outside_workspace, PermissionAction.APPROVAL)
        self.assertEqual(cfg.execution.terminal_commands, PermissionAction.SANDBOX)
        self.assertEqual(cfg.execution.run_tests, PermissionAction.ALLOW)
        self.assertEqual(cfg.execution.install_dependencies, PermissionAction.APPROVAL)
        self.assertEqual(cfg.execution.git_commit, PermissionAction.APPROVAL)
        self.assertEqual(cfg.execution.git_push, PermissionAction.APPROVAL)
        self.assertEqual(cfg.network.mode, NetworkMode.ALLOWLIST)
        self.assertIn("pypi.org", cfg.network.allowed_domains)
        self.assertEqual(cfg.external_actions.deployment, PermissionAction.APPROVAL)

    def test_resolve_restricted_profile(self) -> None:
        cfg = resolve_profile_permissions(PermissionProfile.RESTRICTED)
        self.assertEqual(cfg.profile, PermissionProfile.RESTRICTED)
        self.assertEqual(cfg.filesystem.create_files, PermissionAction.APPROVAL)
        self.assertEqual(cfg.filesystem.modify_files, PermissionAction.APPROVAL)
        self.assertEqual(cfg.execution.terminal_commands, PermissionAction.APPROVAL)
        self.assertEqual(cfg.execution.run_tests, PermissionAction.APPROVAL)
        self.assertEqual(cfg.network.mode, NetworkMode.DISABLED)
        self.assertEqual(cfg.network.allowed_domains, [])

    def test_resolve_autonomous_profile(self) -> None:
        cfg = resolve_profile_permissions(PermissionProfile.AUTONOMOUS)
        self.assertEqual(cfg.profile, PermissionProfile.AUTONOMOUS)
        self.assertEqual(cfg.filesystem.delete_files, PermissionAction.SANDBOX)
        self.assertEqual(cfg.execution.install_dependencies, PermissionAction.SANDBOX)
        self.assertEqual(cfg.execution.git_commit, PermissionAction.ALLOW)
        self.assertEqual(cfg.execution.git_push, PermissionAction.APPROVAL)


class TestStep3Domains(unittest.TestCase):
    """Test Step 3 — Domain Pack Selection."""

    @patch("keplix.cli.wizard.step3_domains.prompt_two_column_domains", return_value=("auto", ["software", "marketing", "content", "data_analytics"]))
    def test_step3_auto(self, mock_prompt) -> None:
        context = SetupContext(total_steps=9)
        success = run_step3_domains(context)
        self.assertTrue(success)
        self.assertIsNotNone(context.domains)
        self.assertEqual(context.domains.mode, DomainMode.AUTO)

    @patch("keplix.cli.wizard.step3_domains.prompt_two_column_domains", return_value=("core_only", []))
    def test_step3_core_only(self, mock_prompt) -> None:
        context = SetupContext(total_steps=9)
        success = run_step3_domains(context)
        self.assertTrue(success)
        self.assertIsNotNone(context.domains)
        self.assertEqual(context.domains.mode, DomainMode.CORE_ONLY)
        self.assertEqual(context.domains.enabled, [])

    @patch("keplix.cli.wizard.step3_domains.prompt_two_column_domains", return_value=("manual", ["software", "marketing", "finance"]))
    def test_step3_manual(self, mock_prompt) -> None:
        context = SetupContext(total_steps=9)
        success = run_step3_domains(context)
        self.assertTrue(success)
        self.assertIsNotNone(context.domains)
        self.assertEqual(context.domains.mode, DomainMode.SPECIALIZED)
        self.assertEqual(context.domains.enabled, ["software", "marketing", "finance"])

    @patch("keplix.cli.wizard.step3_domains.prompt_two_column_domains", return_value=(NAV_BACK, []))
    def test_step3_back_navigation(self, mock_prompt) -> None:
        context = SetupContext(total_steps=9)
        success = run_step3_domains(context)
        self.assertFalse(success)  # Returns False to step back to Step 2


class TestStep4Permissions(unittest.TestCase):
    """Test Step 4 — Capabilities and Permissions Configuration."""

    @patch("keplix.cli.wizard.step4_permissions.prompt_select", return_value="balanced")
    def test_step4_balanced(self, mock_select) -> None:
        context = SetupContext(total_steps=9)
        success = run_step4_permissions(context)
        self.assertTrue(success)
        self.assertIsNotNone(context.permissions)
        self.assertEqual(context.permissions.profile, PermissionProfile.BALANCED)
        self.assertEqual(context.permissions.filesystem.read_workspace, PermissionAction.ALLOW)
        self.assertEqual(context.permissions.filesystem.access_outside_workspace, PermissionAction.APPROVAL)

    @patch("keplix.cli.wizard.step4_permissions.prompt_select", return_value="restricted")
    def test_step4_restricted(self, mock_select) -> None:
        context = SetupContext(total_steps=9)
        success = run_step4_permissions(context)
        self.assertTrue(success)
        self.assertIsNotNone(context.permissions)
        self.assertEqual(context.permissions.profile, PermissionProfile.RESTRICTED)
        self.assertEqual(context.permissions.execution.terminal_commands, PermissionAction.APPROVAL)

    @patch("keplix.cli.wizard.step4_permissions.prompt_select", return_value="autonomous")
    def test_step4_autonomous(self, mock_select) -> None:
        context = SetupContext(total_steps=9)
        success = run_step4_permissions(context)
        self.assertTrue(success)
        self.assertIsNotNone(context.permissions)
        self.assertEqual(context.permissions.profile, PermissionProfile.AUTONOMOUS)
        self.assertEqual(context.permissions.execution.git_commit, PermissionAction.ALLOW)

    @patch("keplix.cli.wizard.step4_permissions.prompt_select", side_effect=["custom", "confirm"])
    def test_step4_custom(self, mock_select) -> None:
        context = SetupContext(total_steps=9)
        success = run_step4_permissions(context)
        self.assertTrue(success)
        self.assertIsNotNone(context.permissions)
        self.assertEqual(context.permissions.profile, PermissionProfile.CUSTOM)

    @patch("keplix.cli.wizard.step4_permissions.prompt_select", return_value=NAV_BACK)
    def test_step4_back_navigation(self, mock_select) -> None:
        context = SetupContext(total_steps=9)
        success = run_step4_permissions(context)
        self.assertFalse(success)  # Returns False to step back to Step 3


class TestWizardControllerFullFlow(unittest.TestCase):
    """Test end-to-end controller chaining from Step 0 to Step 4."""

    def test_full_chain_steps_0_to_4(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            def mock_step0(ctx): return True
            def mock_step1(ctx): return "continue"
            def mock_step2(ctx): return True
            def mock_step3(ctx):
                ctx.domains = DomainConfig(mode=DomainMode.SPECIALIZED, enabled=["software", "research"])
                return True
            def mock_step4(ctx):
                ctx.permissions = resolve_profile_permissions(PermissionProfile.BALANCED)
                return True

            controller = WizardController(
                steps=[mock_step0, mock_step1, mock_step2, mock_step3, mock_step4],
                total_steps=9,
            )
            context = controller.execute(initial_step=0)

            self.assertIsNotNone(context)
            self.assertFalse(context.cancelled)
            self.assertIsNotNone(context.domains)
            self.assertEqual(context.domains.mode, DomainMode.SPECIALIZED)
            self.assertEqual(context.domains.enabled, ["software", "research"])
            self.assertIsNotNone(context.permissions)
            self.assertEqual(context.permissions.profile, PermissionProfile.BALANCED)
            self.assertEqual(context.permissions.filesystem.access_outside_workspace, PermissionAction.APPROVAL)

            # CRITICAL ARCHITECTURAL RULE: Verify no keplix.toml or .keplix was written to disk!
            self.assertFalse((tmp_path / "keplix.toml").exists())
            self.assertFalse((tmp_path / ".keplix").exists())

    def test_backward_navigation_steps_4_to_3_to_2(self) -> None:
        """Verify stepping backward from Step 4 to Step 3, then Step 3 to Step 2."""
        step4_calls = 0
        def mock_step4(ctx):
            nonlocal step4_calls
            step4_calls += 1
            if step4_calls == 1:
                return False  # Go back to Step 3
            ctx.permissions = resolve_profile_permissions(PermissionProfile.BALANCED)
            return True

        step3_calls = 0
        def mock_step3(ctx):
            nonlocal step3_calls
            step3_calls += 1
            ctx.domains = DomainConfig(mode=DomainMode.AUTO, enabled=[])
            return True

        def mock_step2(ctx):
            return True

        # Directly pass the mocked steps into WizardController thanks to Step Registry Pipeline!
        controller = WizardController(
            steps=[None, None, mock_step2, mock_step3, mock_step4],
            total_steps=9,
        )
        context = controller.execute(initial_step=2)

        self.assertIsNotNone(context)
        self.assertEqual(step4_calls, 2)
        self.assertEqual(step3_calls, 2)
        self.assertIsNotNone(context.domains)
        self.assertIsNotNone(context.permissions)


if __name__ == "__main__":
    unittest.main()
