"""Integration tests for Docker sandbox runner and GitGuard checkpoints."""

from pathlib import Path

from keplix.sandbox.docker_runner import DockerSandboxRunner
from keplix.sandbox.git_guard import GitGuard


def test_git_guard_checkpoint_cycle(tmp_path: Path) -> None:
    guard = GitGuard(repo_path=tmp_path)
    file = tmp_path / "test.txt"
    file.write_text("initial state\n", encoding="utf-8")

    # Initial checkpoint
    sha1 = guard.create_checkpoint("task_init")
    assert sha1 != ""

    # Modify file
    file.write_text("corrupted bad state\n", encoding="utf-8")
    assert guard.is_dirty()

    # Rollback
    guard.rollback_to(sha1)
    assert file.read_text(encoding="utf-8") == "initial state\n"


def test_docker_runner_availability_probe() -> None:
    runner = DockerSandboxRunner()
    # Ensure probe executes without uncaught exceptions
    status = runner.is_available()
    assert isinstance(status, bool)

