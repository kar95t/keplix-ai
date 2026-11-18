"""Comprehensive unit tests for Keplix CLI First-Run Setup Wizard (Steps 0–2).

Compatible with both standard library unittest and pytest test runners.
"""

import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from keplix.cli.wizard.context import (
    EnvironmentInfo,
    SetupContext,
    WorkspaceInspectionResult,
    WorkspaceState,
)
from keplix.cli.wizard.controller import WizardController, run_init_wizard
from keplix.cli.wizard.detector import (
    detect_cwd,
    detect_docker,
    detect_git,
    detect_keyring,
    detect_os,
    detect_provider_keys,
    detect_python,
    detect_workspace_artifacts,
    run_environment_detection,
)
from keplix.cli.wizard.inspector import WorkspaceInspector
from keplix.cli.wizard.paths import WorkspacePaths
from keplix.cli.wizard.step0_welcome import run_step0_welcome
from keplix.cli.wizard.step1_env import run_step1_environment
from keplix.cli.wizard.step2_workspace import (
    handle_existing_workspace,
    handle_invalid_configuration,
    handle_partial_runtime,
    resolve_candidate_path,
    run_option1_current_directory,
    run_option2_choose_directory,
    run_option3_create_directory,
    run_step2_workspace,
    validate_project_name,
)
from keplix.cli.wizard.ui import (
    NAV_BACK,
    WizardCancelledException,
    badge_experimental,
    badge_not_recommended,
    badge_recommended,
    badge_stable,
    format_path_display,
    prompt_select,
    render_wizard_header,
)


class TestUIAndPaths(unittest.TestCase):
    """Test UI rendering helpers, badge markup, and path managers."""

    def test_workspace_paths_immutability(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            paths = WorkspacePaths(root=tmp_path)
            self.assertEqual(paths.root, tmp_path.resolve())
            self.assertEqual(paths.config_file, tmp_path.resolve() / "keplix.toml")
            self.assertEqual(paths.runtime_dir, tmp_path.resolve() / ".keplix")
            self.assertEqual(paths.state_db, tmp_path.resolve() / ".keplix" / "state.db")
            self.assertEqual(paths.runs_dir, tmp_path.resolve() / ".keplix" / "runs")
            self.assertEqual(paths.logs_dir, tmp_path.resolve() / ".keplix" / "logs")
            self.assertEqual(paths.traces_dir, tmp_path.resolve() / ".keplix" / "traces")
            self.assertEqual(paths.cache_dir, tmp_path.resolve() / ".keplix" / "cache")
            self.assertEqual(paths.indexes_dir, tmp_path.resolve() / ".keplix" / "indexes")
            self.assertEqual(paths.gitignore_file, tmp_path.resolve() / ".gitignore")

            # Verify paths are NOT created on disk prematurely
            self.assertFalse(paths.runtime_dir.exists())
            self.assertFalse(paths.config_file.exists())

            # Immutability
            with self.assertRaises(Exception):
                paths.root = Path("/other")  # type: ignore[misc]

    def test_badge_rendering(self) -> None:
        self.assertIn("RECOMMENDED", badge_recommended())
        self.assertIn("STABLE", badge_stable())
        self.assertIn("EXPERIMENTAL", badge_experimental())
        self.assertIn("NOT RECOMMENDED", badge_not_recommended())

    def test_format_path_display(self) -> None:
        home = Path.home()
        sub_path = home / "projects" / "weather-dashboard"
        disp = format_path_display(sub_path)
        self.assertTrue(disp.startswith("~/") or "projects/weather-dashboard" in disp)

    def test_render_wizard_header(self) -> None:
        # Verify no unhandled exceptions
        render_wizard_header(current_step=1, total_steps=9, completed_steps=set())
        render_wizard_header(current_step=2, total_steps=9, completed_steps={1})

    def test_render_keplix_brand_banner_option_a(self) -> None:
        """Verify Option A banner renders with isometric cube and clean block font."""
        from keplix.cli.wizard.ui import render_keplix_brand_banner, KEPLIX_ASCII_LOGO, KEPLIX_BANNER_OPTION_A
        self.assertIn("╭───╮", KEPLIX_ASCII_LOGO)
        self.assertIn("Your AI coding workforce, orchestrated.", KEPLIX_ASCII_LOGO)
        self.assertIn("╭───╮", KEPLIX_BANNER_OPTION_A)
        # Check execution does not crash
        render_keplix_brand_banner()

    def test_prompt_select_non_interactive(self) -> None:
        """Verify non-interactive prompt_select works with piped input."""
        options = [
            {"id": "opt1", "title": "Option 1", "badges": ["RECOMMENDED"]},
            {"id": "opt2", "title": "Option 2", "badges": []},
        ]
        with patch("sys.stdin", io.StringIO("2\n")):
            res = prompt_select("Test", options)
            self.assertEqual(res, "opt2")

    def test_prompt_select_interactive_navigation(self) -> None:
        """Verify interactive Live display navigation with UP/DOWN/ENTER keys."""
        options = [
            {"id": "opt1", "title": "Option 1", "badges": ["RECOMMENDED"]},
            {"id": "opt2", "title": "Option 2", "badges": []},
            {"id": "opt3", "title": "Option 3", "badges": []},
        ]
        # Simulate DOWN then ENTER -> selects opt2
        keys = ["DOWN", "ENTER"]
        with patch("sys.stdin.isatty", return_value=True):
            with patch("keplix.cli.wizard.ui._get_key", side_effect=lambda: keys.pop(0)):
                res = prompt_select("Test", options, default_idx=0)
                self.assertEqual(res, "opt2")

    def test_prompt_select_interactive_esc(self) -> None:
        """Verify ESC key returns NAV_BACK."""
        options = [{"id": "opt1", "title": "Option 1", "badges": []}]
        with patch("sys.stdin.isatty", return_value=True):
            with patch("keplix.cli.wizard.ui._get_key", return_value="ESC"):
                res = prompt_select("Test", options, allow_back=True)
                self.assertEqual(res, NAV_BACK)

    def test_prompt_select_interactive_cancel(self) -> None:
        """Verify Ctrl+C raises WizardCancelledException."""
        options = [{"id": "opt1", "title": "Option 1", "badges": []}]
        with patch("sys.stdin.isatty", return_value=True):
            with patch("keplix.cli.wizard.ui._get_key", side_effect=KeyboardInterrupt):
                with self.assertRaises(WizardCancelledException):
                    prompt_select("Test", options)


class TestStep0Welcome(unittest.TestCase):
    """Test Step 0 — Welcome screen behavior and input handling."""

    @patch("sys.stdin", io.StringIO("\n"))
    def test_welcome_enter(self) -> None:
        context = SetupContext(total_steps=9)
        result = run_step0_welcome(context)
        self.assertTrue(result)

    @patch("keplix.cli.wizard.ui._get_key", side_effect=KeyboardInterrupt)
    @patch("sys.stdin.isatty", return_value=True)
    def test_welcome_ctrl_c(self, mock_isatty, mock_get_key) -> None:
        context = SetupContext(total_steps=9)
        with self.assertRaises(WizardCancelledException):
            run_step0_welcome(context)

    def test_welcome_non_interactive(self) -> None:
        context = SetupContext(total_steps=9)
        with patch("sys.stdin.isatty", return_value=False):
            with patch("sys.stdin", io.StringIO("")):
                result = run_step0_welcome(context)
                self.assertTrue(result)


class TestStep1EnvironmentDetection(unittest.TestCase):
    """Test Step 1 — Read-only environment inspection across all subsystems."""

    @patch("platform.system", return_value="Windows")
    @patch("platform.release", return_value="11")
    def test_detect_os_windows(self, mock_rel, mock_sys) -> None:
        os_name, os_ver = detect_os()
        self.assertEqual(os_name, "Windows")
        self.assertIn("Windows 11", os_ver)

    @patch("platform.system", return_value="Darwin")
    @patch("platform.mac_ver", return_value=("14.2.1", ("", "", ""), ""))
    def test_detect_os_macos(self, mock_mac, mock_sys) -> None:
        os_name, os_ver = detect_os()
        self.assertEqual(os_name, "macOS")
        self.assertIn("14.2.1", os_ver)

    @patch("platform.system", return_value="Linux")
    @patch("platform.release", return_value="6.5.0")
    def test_detect_os_linux(self, mock_rel, mock_sys) -> None:
        os_name, os_ver = detect_os()
        self.assertEqual(os_name, "Linux")
        self.assertIn("6.5.0", os_ver)

    @patch("platform.system", return_value="FreeBSD")
    @patch("platform.release", return_value="14.0")
    def test_detect_os_unknown(self, mock_rel, mock_sys) -> None:
        os_name, os_ver = detect_os()
        self.assertEqual(os_name, "Unknown")

    @patch("sys.version_info", (3, 12, 2, "final", 0))
    def test_detect_python_supported(self) -> None:
        ver, exe, supported = detect_python(min_version=(3, 12))
        self.assertTrue(supported)

    @patch("sys.version_info", (3, 11, 8, "final", 0))
    def test_detect_python_unsupported(self) -> None:
        ver, exe, supported = detect_python(min_version=(3, 12))
        self.assertFalse(supported)

    def test_detect_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            path, exists, readable, writable = detect_cwd(tmp_path)
            self.assertEqual(path, tmp_path.resolve())
            self.assertTrue(exists)
            self.assertTrue(readable)
            self.assertTrue(writable)

    @patch("shutil.which", return_value=None)
    def test_detect_git_missing(self, mock_which) -> None:
        avail, ver, is_repo, root, branch, detached = detect_git()
        self.assertFalse(avail)
        self.assertFalse(is_repo)

    @patch("shutil.which", return_value="/usr/bin/git")
    def test_detect_git_not_a_repo(self, mock_which) -> None:
        def mock_subproc(args, **kwargs):
            cmd = " ".join(args)
            if "--version" in cmd:
                return MagicMock(returncode=0, stdout="git version 2.43.0\n")
            if "--is-inside-work-tree" in cmd:
                return MagicMock(returncode=128, stdout="fatal: not a git repository\n")
            return MagicMock(returncode=1, stdout="")

        with patch("subprocess.run", side_effect=mock_subproc):
            avail, ver, is_repo, root, branch, detached = detect_git()
            self.assertTrue(avail)
            self.assertIn("2.43.0", ver)
            self.assertFalse(is_repo)

    @patch("shutil.which", return_value="/usr/bin/git")
    def test_detect_git_active_repo(self, mock_which) -> None:
        def mock_subproc(args, **kwargs):
            cmd = " ".join(args)
            if "--version" in cmd:
                return MagicMock(returncode=0, stdout="git version 2.43.0\n")
            if "--is-inside-work-tree" in cmd:
                return MagicMock(returncode=0, stdout="true\n")
            if "--show-toplevel" in cmd:
                return MagicMock(returncode=0, stdout="/path/to/repo\n")
            if "branch --show-current" in cmd:
                return MagicMock(returncode=0, stdout="main\n")
            return MagicMock(returncode=1, stdout="")

        with patch("subprocess.run", side_effect=mock_subproc):
            avail, ver, is_repo, root, branch, detached = detect_git()
            self.assertTrue(avail)
            self.assertTrue(is_repo)
            self.assertEqual(branch, "main")
            self.assertFalse(detached)

    @patch("shutil.which", return_value=None)
    def test_detect_docker_missing(self, mock_which) -> None:
        avail, ver, daemon, srv_ver = detect_docker()
        self.assertFalse(avail)
        self.assertFalse(daemon)

    @patch("shutil.which", return_value="/usr/bin/docker")
    def test_detect_docker_daemon_running(self, mock_which) -> None:
        def mock_subproc(args, **kwargs):
            cmd = " ".join(args)
            if "--version" in cmd:
                return MagicMock(returncode=0, stdout="Docker version 26.1.0\n")
            if "info" in cmd:
                return MagicMock(returncode=0, stdout="26.1.0\n")
            return MagicMock(returncode=1, stdout="")

        with patch("subprocess.run", side_effect=mock_subproc):
            with patch.dict(sys.modules, {"docker": None}):
                avail, ver, daemon, srv_ver = detect_docker()
                self.assertTrue(avail)
                self.assertIn("26.1.0", ver)
                self.assertTrue(daemon)

    def test_detect_provider_keys_zero_leakage(self) -> None:
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-real-secret-12345", "ANTHROPIC_API_KEY": ""}):
            keys = detect_provider_keys()
            self.assertTrue(keys["OPENAI_API_KEY"])
            self.assertFalse(keys["ANTHROPIC_API_KEY"])
            # Ensure plaintext secret value is nowhere in the returned dictionary
            for val in keys.values():
                self.assertIsInstance(val, bool)

    def test_detect_workspace_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            (tmp_path / "keplix.toml").write_text("", encoding="utf-8")
            (tmp_path / ".keplix").mkdir()

            has_toml, has_runtime, has_gitignore = detect_workspace_artifacts(tmp_path)
            self.assertTrue(has_toml)
            self.assertTrue(has_runtime)
            self.assertFalse(has_gitignore)

    @patch("sys.version_info", (3, 12, 1, "final", 0))
    @patch("keplix.cli.wizard.step1_env.prompt_select", return_value="continue")
    def test_step1_continue(self, mock_select) -> None:
        context = SetupContext(total_steps=9)
        action = run_step1_environment(context)
        self.assertEqual(action, "continue")
        self.assertIsNotNone(context.env_info)
        self.assertTrue(context.env_info.all_required_passed)

    @patch("sys.version_info", (3, 12, 1, "final", 0))
    def test_step1_recheck(self) -> None:
        context = SetupContext(total_steps=9)
        calls = 0

        def mock_select(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                return "recheck"
            return "continue"

        with patch("keplix.cli.wizard.step1_env.prompt_select", side_effect=mock_select):
            action = run_step1_environment(context)
            self.assertEqual(action, "continue")
            self.assertEqual(calls, 2)

    @patch("keplix.cli.wizard.step1_env.prompt_select", return_value="exit")
    def test_step1_exit(self, mock_select) -> None:
        context = SetupContext(total_steps=9)
        with self.assertRaises(WizardCancelledException):
            run_step1_environment(context)


class TestStep2Workspace(unittest.TestCase):
    """Test Step 2 — Workspace configuration, inspection service, and all scenarios A–E."""

    def test_inspector_scenario_a_fresh(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            res = WorkspaceInspector.inspect(Path(tmp_dir))
            self.assertEqual(res.state, WorkspaceState.FRESH_WORKSPACE)
            self.assertFalse(res.has_toml)
            self.assertFalse(res.has_runtime)

    def test_inspector_scenario_b_existing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            (tmp_path / "keplix.toml").write_text("[execution]\nmax_retries = 3\n", encoding="utf-8")
            (tmp_path / ".keplix").mkdir()

            res = WorkspaceInspector.inspect(tmp_path)
            self.assertEqual(res.state, WorkspaceState.EXISTING_WORKSPACE)
            self.assertTrue(res.has_toml)
            self.assertTrue(res.has_runtime)
            self.assertTrue(res.is_config_valid)

    def test_inspector_scenario_c_config_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            (tmp_path / "keplix.toml").write_text("[execution]\nmax_retries = 2\n", encoding="utf-8")

            res = WorkspaceInspector.inspect(tmp_path)
            self.assertEqual(res.state, WorkspaceState.EXISTING_CONFIGURATION)
            self.assertTrue(res.has_toml)
            self.assertFalse(res.has_runtime)
            self.assertTrue(res.is_config_valid)

    def test_inspector_scenario_d_partial_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            (tmp_path / ".keplix").mkdir()

            res = WorkspaceInspector.inspect(tmp_path)
            self.assertEqual(res.state, WorkspaceState.PARTIAL_RUNTIME)
            self.assertFalse(res.has_toml)
            self.assertTrue(res.has_runtime)

    def test_inspector_scenario_e_invalid_toml(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            (tmp_path / "keplix.toml").write_text("invalid_toml = [broken syntax", encoding="utf-8")

            res = WorkspaceInspector.inspect(tmp_path)
            self.assertEqual(res.state, WorkspaceState.INVALID_CONFIGURATION)
            self.assertTrue(res.has_toml)
            self.assertFalse(res.is_config_valid)
            self.assertGreater(len(res.validation_errors), 0)

    def test_handle_existing_workspace_continue(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            (tmp_path / "keplix.toml").write_text("[execution]\nmax_retries = 3\n", encoding="utf-8")
            (tmp_path / ".keplix").mkdir()
            inspection = WorkspaceInspector.inspect(tmp_path)

            context = SetupContext(total_steps=9)
            with patch("keplix.cli.wizard.step2_workspace.prompt_select", return_value="continue"):
                success = handle_existing_workspace(context, tmp_path, inspection)
                self.assertTrue(success)
                self.assertEqual(context.config_action, "continue")

    def test_handle_existing_workspace_reconfigure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            (tmp_path / "keplix.toml").write_text("[execution]\nmax_retries = 3\n", encoding="utf-8")
            (tmp_path / ".keplix").mkdir()
            inspection = WorkspaceInspector.inspect(tmp_path)

            context = SetupContext(total_steps=9)
            with patch("keplix.cli.wizard.step2_workspace.prompt_select", return_value="reconfigure"):
                success = handle_existing_workspace(context, tmp_path, inspection)
                self.assertTrue(success)
                self.assertEqual(context.config_action, "reconfigure")

    def test_handle_existing_workspace_cancel(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            (tmp_path / "keplix.toml").write_text("[execution]\nmax_retries = 3\n", encoding="utf-8")
            (tmp_path / ".keplix").mkdir()
            inspection = WorkspaceInspector.inspect(tmp_path)

            context = SetupContext(total_steps=9)
            with patch("keplix.cli.wizard.step2_workspace.prompt_select", return_value="cancel"):
                with self.assertRaises(WizardCancelledException):
                    handle_existing_workspace(context, tmp_path, inspection)

    def test_handle_partial_runtime_preserve(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            (tmp_path / ".keplix").mkdir()
            inspection = WorkspaceInspector.inspect(tmp_path)

            context = SetupContext(total_steps=9)
            with patch("keplix.cli.wizard.step2_workspace.prompt_select", return_value="preserve"):
                success = handle_partial_runtime(context, tmp_path, inspection)
                self.assertTrue(success)
                self.assertEqual(context.config_action, "preserve")
                self.assertTrue(context.is_partial_workspace)

    def test_handle_invalid_configuration_exit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            (tmp_path / "keplix.toml").write_text("broken = [syntax", encoding="utf-8")
            inspection = WorkspaceInspector.inspect(tmp_path)

            context = SetupContext(total_steps=9)
            with patch("keplix.cli.wizard.step2_workspace.prompt_select", return_value="exit"):
                with self.assertRaises(WizardCancelledException):
                    handle_invalid_configuration(context, tmp_path, inspection)

    def test_validate_project_name(self) -> None:
        # Valid names
        self.assertTrue(validate_project_name("weather-dashboard")[0])
        self.assertTrue(validate_project_name("backend_api_v2")[0])
        self.assertTrue(validate_project_name("microservice-1")[0])

        # Empty
        self.assertFalse(validate_project_name("   ")[0])

        # Traversal and separators
        self.assertFalse(validate_project_name("a/b")[0])
        self.assertFalse(validate_project_name("a\\b")[0])
        self.assertFalse(validate_project_name("..")[0])
        self.assertFalse(validate_project_name(".")[0])
        self.assertFalse(validate_project_name("../escape")[0])

        # Invalid characters
        self.assertFalse(validate_project_name("test*")[0])
        self.assertFalse(validate_project_name("test:proj")[0])
        self.assertFalse(validate_project_name("proj?")[0])

        # Trailing dot or space
        self.assertFalse(validate_project_name("proj.")[0])
        self.assertFalse(validate_project_name("proj ")[0])

        # Windows reserved names
        self.assertFalse(validate_project_name("CON")[0])
        self.assertFalse(validate_project_name("con.txt")[0])
        self.assertFalse(validate_project_name("NUL")[0])
        self.assertFalse(validate_project_name("aux")[0])
        self.assertFalse(validate_project_name("prn")[0])
        self.assertFalse(validate_project_name("COM1")[0])
        self.assertFalse(validate_project_name("LPT2")[0])

    def test_resolve_candidate_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # Valid directory
            res, err = resolve_candidate_path(str(tmp_path))
            self.assertEqual(res, tmp_path.resolve())
            self.assertIsNone(err)

            # Non-existent
            res, err = resolve_candidate_path(str(tmp_path / "non_existent"))
            self.assertIsNone(res)
            self.assertIn("does not exist", err)

            # File
            file = tmp_path / "test.txt"
            file.write_text("hello", encoding="utf-8")
            res, err = resolve_candidate_path(str(file))
            self.assertIsNone(res)
            self.assertIn("is a file", err)

    def test_option1_use_current_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            orig_cwd = os.getcwd()
            os.chdir(tmp_path)
            try:
                context = SetupContext(total_steps=9)
                success = run_option1_current_directory(context)
                self.assertTrue(success)
                self.assertEqual(context.selected_path, tmp_path.resolve())
                self.assertEqual(context.selection_method, "current")
                self.assertFalse(context.is_new_workspace)
                # Ensure no files created prematurely
                self.assertFalse((tmp_path / "keplix.toml").exists())
                self.assertFalse((tmp_path / ".keplix").exists())
            finally:
                os.chdir(orig_cwd)

    def test_option2_choose_another_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            target = tmp_path / "other-project"
            target.mkdir()

            context = SetupContext(total_steps=9)
            with patch("keplix.cli.wizard.step2_workspace.prompt_text_input", return_value=str(target)):
                with patch("keplix.cli.wizard.step2_workspace.prompt_select", return_value="continue"):
                    success = run_option2_choose_directory(context)
                    self.assertTrue(success)
                    self.assertEqual(context.selected_path, target.resolve())
                    self.assertEqual(context.selection_method, "choose")

    def test_option3_create_directory_non_existent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            parent = tmp_path / "parent"
            parent.mkdir()

            context = SetupContext(total_steps=9)
            inputs = [str(parent), "new-project"]

            def mock_input(*args, **kwargs):
                return inputs.pop(0)

            with patch("keplix.cli.wizard.step2_workspace.prompt_text_input", side_effect=mock_input):
                with patch("keplix.cli.wizard.step2_workspace.prompt_select", return_value="create"):
                    success = run_option3_create_directory(context)
                    self.assertTrue(success)
                    expected = (parent / "new-project").resolve()
                    self.assertEqual(context.selected_path, expected)
                    self.assertTrue(context.is_new_workspace)
                    self.assertTrue(expected.exists())
                    # Ensure no premature configuration files or git init
                    self.assertFalse((expected / "keplix.toml").exists())
                    self.assertFalse((expected / ".keplix").exists())
                    self.assertFalse((expected / ".git").exists())

    def test_option3_create_directory_already_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            parent = tmp_path / "parent"
            parent.mkdir()
            existing = parent / "existing-proj"
            existing.mkdir()

            context = SetupContext(total_steps=9)
            inputs = [str(parent), "existing-proj"]

            def mock_input(*args, **kwargs):
                return inputs.pop(0)

            with patch("keplix.cli.wizard.step2_workspace.prompt_text_input", side_effect=mock_input):
                with patch("keplix.cli.wizard.step2_workspace.prompt_select", return_value="use_existing"):
                    success = run_option3_create_directory(context)
                    self.assertTrue(success)
                    self.assertEqual(context.selected_path, existing.resolve())
                    self.assertFalse(context.is_new_workspace)

    def test_step2_main_back_navigation(self) -> None:
        context = SetupContext(total_steps=9)
        with patch("keplix.cli.wizard.step2_workspace.prompt_select", return_value=NAV_BACK):
            success = run_step2_workspace(context)
            self.assertFalse(success)  # False indicates back navigation to Step 1


class TestWizardController(unittest.TestCase):
    """Test full controller execution across Steps 0, 1, and 2."""

    def test_controller_end_to_end_flow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            orig_cwd = os.getcwd()
            os.chdir(tmp_path)
            try:
                with patch("sys.version_info", (3, 12, 1, "final", 0)):
                    with patch("keplix.cli.wizard.step0_welcome.prompt_press_enter", return_value=None):
                        with patch("keplix.cli.wizard.step1_env.prompt_select", return_value="continue"):
                            with patch("keplix.cli.wizard.step2_workspace.prompt_select", return_value="current"):
                                context = run_init_wizard(total_steps=9)
                                self.assertIsNotNone(context)
                                self.assertFalse(context.cancelled)
                                self.assertEqual(context.selected_path, tmp_path.resolve())
                                self.assertEqual(context.inspection.state, WorkspaceState.FRESH_WORKSPACE)
            finally:
                os.chdir(orig_cwd)

    def test_controller_back_and_forward_flow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            orig_cwd = os.getcwd()
            os.chdir(tmp_path)
            try:
                step2_calls = 0

                def mock_step2_select(*args, **kwargs):
                    nonlocal step2_calls
                    step2_calls += 1
                    if step2_calls == 1:
                        return NAV_BACK  # Go back to Step 1
                    return "current"

                with patch("sys.version_info", (3, 12, 1, "final", 0)):
                    with patch("keplix.cli.wizard.step0_welcome.prompt_press_enter", return_value=None):
                        with patch("keplix.cli.wizard.step1_env.prompt_select", return_value="continue"):
                            with patch("keplix.cli.wizard.step2_workspace.prompt_select", side_effect=mock_step2_select):
                                context = run_init_wizard(total_steps=9)
                                self.assertIsNotNone(context)
                                self.assertEqual(step2_calls, 2)
                                self.assertEqual(context.selected_path, tmp_path.resolve())
            finally:
                os.chdir(orig_cwd)

    def test_controller_cancellation(self) -> None:
        with patch("keplix.cli.wizard.step0_welcome.prompt_press_enter", side_effect=WizardCancelledException):
            context = run_init_wizard(total_steps=9)
            self.assertIsNone(context)


if __name__ == "__main__":
    unittest.main()
