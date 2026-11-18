"""Pure read-only system and workspace environment detection for Keplix."""

import importlib.util
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from typing import Optional

from keplix.cli.wizard.context import EnvironmentInfo


def detect_os() -> tuple[str, str]:
    """Detect operating system name and version.

    Returns:
        (os_name, os_version) where os_name is Windows, macOS, Linux, or Unknown.
    """
    sys_name = platform.system()
    if sys_name == "Windows":
        return "Windows", f"Windows {platform.release()}"
    elif sys_name == "Darwin":
        mac_ver = platform.mac_ver()[0] or platform.release()
        return "macOS", f"macOS {mac_ver}"
    elif sys_name == "Linux":
        return "Linux", f"Linux {platform.release()}"
    else:
        return "Unknown", f"{sys_name} {platform.release()}"


def detect_python(min_version: tuple[int, int] = (3, 12)) -> tuple[str, str, bool]:
    """Detect Python version, executable path, and check whether it satisfies min_version.

    Returns:
        (version_str, executable_path, is_supported)
    """
    ver = platform.python_version()
    executable = sys.executable
    is_supported = sys.version_info >= min_version
    return ver, executable, is_supported


def detect_cwd(target_path: Optional[Path] = None) -> tuple[Path, bool, bool, bool]:
    """Inspect directory existence, resolution, and read/write permissions.

    Returns:
        (resolved_path, exists, is_readable, is_writable)
    """
    path = (target_path or Path.cwd()).resolve()
    exists = path.is_dir()
    readable = os.access(path, os.R_OK) if exists else False
    writable = os.access(path, os.W_OK) if exists else False
    return path, exists, readable, writable


def detect_git(repo_dir: Optional[Path] = None) -> tuple[bool, Optional[str], bool, Optional[Path], Optional[str], bool]:
    """Detect Git executable, version, repository membership, branch, and detached HEAD.

    Git is optional.

    Returns:
        (git_available, git_version, is_repo, repo_root, branch_name, is_detached)
    """
    target = (repo_dir or Path.cwd()).resolve()
    git_bin = shutil.which("git")
    if not git_bin:
        return False, None, False, None, None, False

    # Get Git version
    git_version = None
    try:
        proc = subprocess.run(
            [git_bin, "--version"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if proc.returncode == 0:
            git_version = proc.stdout.strip()
    except Exception:
        pass

    # Check if target is inside a git repository
    is_repo = False
    repo_root = None
    branch_name = None
    is_detached = False

    try:
        # Check inside work tree
        proc = subprocess.run(
            [git_bin, "rev-parse", "--is-inside-work-tree"],
            cwd=str(target),
            capture_output=True,
            text=True,
            timeout=3,
        )
        if proc.returncode == 0 and "true" in proc.stdout.lower():
            is_repo = True

            # Get repo root
            root_proc = subprocess.run(
                [git_bin, "rev-parse", "--show-toplevel"],
                cwd=str(target),
                capture_output=True,
                text=True,
                timeout=3,
            )
            if root_proc.returncode == 0:
                repo_root = Path(root_proc.stdout.strip()).resolve()

            # Get branch name
            branch_proc = subprocess.run(
                [git_bin, "branch", "--show-current"],
                cwd=str(target),
                capture_output=True,
                text=True,
                timeout=3,
            )
            if branch_proc.returncode == 0 and branch_proc.stdout.strip():
                branch_name = branch_proc.stdout.strip()
            else:
                # Check for detached HEAD
                status_proc = subprocess.run(
                    [git_bin, "status", "--porcelain=v2", "--branch"],
                    cwd=str(target),
                    capture_output=True,
                    text=True,
                    timeout=3,
                )
                if status_proc.returncode == 0 and "branch.oid" in status_proc.stdout:
                    is_detached = True
                    branch_name = "(detached HEAD)"

    except Exception:
        pass

    return True, git_version, is_repo, repo_root, branch_name, is_detached


def detect_docker() -> tuple[bool, Optional[str], bool, Optional[str]]:
    """Detect Docker CLI availability and Docker daemon status without starting Docker.

    Docker is optional. Never starts Docker automatically.

    Returns:
        (cli_available, cli_version, daemon_running, server_version)
    """
    docker_bin = shutil.which("docker")
    if not docker_bin:
        return False, None, False, None

    cli_version = None
    try:
        proc = subprocess.run(
            [docker_bin, "--version"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if proc.returncode == 0:
            cli_version = proc.stdout.strip()
    except Exception:
        pass

    # Probe daemon availability with a short timeout
    daemon_running = False
    server_version = None

    # First attempt: Python docker SDK if available
    try:
        import docker
        client = docker.from_env()
        # ping with short timeout
        if client.ping():
            daemon_running = True
            try:
                version_info = client.version()
                server_version = version_info.get("Version")
            except Exception:
                pass
    except Exception:
        # Fallback to docker info CLI probe with 2 second timeout
        try:
            info_proc = subprocess.run(
                [docker_bin, "info", "--format", "{{.ServerVersion}}"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if info_proc.returncode == 0 and info_proc.stdout.strip():
                daemon_running = True
                server_version = info_proc.stdout.strip()
        except Exception:
            pass

    return True, cli_version, daemon_running, server_version


def detect_keplix() -> tuple[str, bool]:
    """Verify Keplix installation and importability.

    Returns:
        (keplix_version, is_importable)
    """
    try:
        import keplix
        ver = getattr(keplix, "__version__", "0.1.0")
        return ver, True
    except ImportError:
        return "0.1.0", False


def detect_workspace_artifacts(target_path: Optional[Path] = None) -> tuple[bool, bool, bool]:
    """Check for existing keplix.toml, .keplix/ directory, and .gitignore.

    Returns:
        (has_toml, has_runtime, has_gitignore)
    """
    path = (target_path or Path.cwd()).resolve()
    has_toml = (path / "keplix.toml").is_file()
    has_runtime = (path / ".keplix").is_dir()
    has_gitignore = (path / ".gitignore").is_file()
    return has_toml, has_runtime, has_gitignore


def detect_keyring() -> tuple[bool, Optional[str], int, bool]:
    """Detect whether keyring library is available and has a functional backend.

    Does NOT write test credentials.

    Returns:
        (keyring_available, backend_name, priority, is_usable)
    """
    try:
        import keyring
        backend = keyring.get_keyring()
        name = getattr(backend, "name", backend.__class__.__name__)
        priority = getattr(backend, "priority", 0)

        # Check for fail / dummy backends (priority <= 0 or explicit fail backends)
        is_usable = priority > 0 and "fail" not in name.lower() and "null" not in name.lower()
        return True, name, int(priority), is_usable
    except Exception:
        return False, None, 0, False


def detect_provider_keys() -> dict[str, bool]:
    """Check presence of provider API keys in environment variables.

    NEVER returns or logs the secret values, only presence booleans!
    """
    checked_keys = [
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "DEEPSEEK_API_KEY",
        "GROQ_API_KEY",
        "GOOGLE_API_KEY",
        "GEMINI_API_KEY",
    ]
    return {k: bool(os.getenv(k)) for k in checked_keys}


def run_environment_detection(cwd: Optional[Path] = None) -> EnvironmentInfo:
    """Execute complete read-only environment detection across all subsystems.

    Never modifies files, env vars, or directories.
    """
    target = cwd or Path.cwd()

    os_name, os_version = detect_os()
    py_ver, py_exec, py_supported = detect_python(min_version=(3, 12))
    resolved_cwd, cwd_exists, cwd_read, cwd_write = detect_cwd(target)
    git_avail, git_ver, is_repo, git_root, git_branch, git_detached = detect_git(target)
    docker_cli, docker_cli_ver, docker_daemon, docker_srv_ver = detect_docker()
    keplix_ver, keplix_ok = detect_keplix()
    has_toml, has_runtime, has_gitignore = detect_workspace_artifacts(target)
    keyring_avail, keyring_name, keyring_pri, keyring_usable = detect_keyring()
    provider_keys = detect_provider_keys()

    warnings: list[str] = []
    errors: list[str] = []

    # Required checks
    if not py_supported:
        errors.append(f"Python {py_ver} is unsupported. Keplix requires Python >= 3.12.")
    if not cwd_exists:
        errors.append(f"Current working directory {resolved_cwd} does not exist.")
    elif not (cwd_read and cwd_write):
        errors.append(f"Insufficient read/write permissions in {resolved_cwd}.")

    # Optional checks (warnings only, never fatal)
    if not git_avail:
        warnings.append("Git CLI not found. Version control checkpoints will be disabled.")
    elif not is_repo:
        warnings.append("Current directory is not a Git repository. Rollback guardrails require Git.")

    if not docker_cli:
        warnings.append("Docker CLI not found. Ephemeral container sandbox will be disabled.")
    elif not docker_daemon:
        warnings.append("Docker daemon is not running. Code execution sandbox will fall back to local.")

    if not (keyring_avail and keyring_usable):
        warnings.append("Encrypted OS keyring backend unavailable. Credentials will fall back to .env.")

    if not any(provider_keys.values()):
        warnings.append("No LLM provider API keys detected in environment (can configure in Step 5).")

    all_required_passed = len(errors) == 0

    return EnvironmentInfo(
        os_name=os_name,
        os_version=os_version,
        python_version=py_ver,
        python_executable=py_exec,
        python_supported=py_supported,
        cwd=resolved_cwd,
        cwd_readable=cwd_read,
        cwd_writable=cwd_write,
        git_available=git_avail,
        git_version=git_ver,
        is_git_repo=is_repo,
        git_root=git_root,
        git_branch=git_branch,
        git_detached=git_detached,
        docker_cli_available=docker_cli,
        docker_cli_version=docker_cli_ver,
        docker_daemon_running=docker_daemon,
        docker_server_version=docker_srv_ver,
        keplix_version=keplix_ver,
        keplix_importable=keplix_ok,
        has_toml=has_toml,
        has_runtime=has_runtime,
        has_gitignore=has_gitignore,
        keyring_available=keyring_avail,
        keyring_backend=keyring_name,
        keyring_priority=keyring_pri,
        keyring_usable=keyring_usable,
        provider_keys=provider_keys,
        all_required_passed=all_required_passed,
        warnings=warnings,
        errors=errors,
    )

