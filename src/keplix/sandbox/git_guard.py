"""Git checkpoint guardrails: auto-commits before edits and automatic rollbacks on failure."""

from pathlib import Path
from typing import Optional

try:
    import git
    from git import InvalidGitRepositoryError, Repo
except ImportError:
    git = None  # type: ignore[assignment]
    Repo = None  # type: ignore[assignment,misc]
    InvalidGitRepositoryError = Exception  # type: ignore[assignment,misc]


class GitGuard:
    """Manages Git-based rollback safety nets for autonomous agent interventions."""

    def __init__(self, repo_path: Optional[Path] = None) -> None:
        self.repo_path = (repo_path or Path.cwd()).resolve()
        self._repo: Optional[Repo] = None

    def _get_repo(self) -> Repo:
        if git is None or Repo is None:
            raise RuntimeError("GitPython is not installed. Install with `uv pip install gitpython`.")
        if self._repo is None:
            try:
                self._repo = Repo(self.repo_path, search_parent_directories=True)
            except InvalidGitRepositoryError:
                # Initialize new git repository if absent
                self._repo = Repo.init(self.repo_path)
        return self._repo

    def get_head_sha(self) -> str:
        """Return the current HEAD commit hash."""
        repo = self._get_repo()
        try:
            return repo.head.commit.hexsha
        except ValueError:
            # Empty repo with no commits yet
            return ""

    def create_checkpoint(self, task_id: str) -> str:
        """Stage uncommitted changes and create a checkpoint commit before task execution."""
        repo = self._get_repo()
        try:
            # Stage all current tracked and untracked changes
            repo.git.add(A=True)
            if repo.is_dirty(untracked_files=True):
                commit = repo.index.commit(f"[keplix checkpoint] Pre-execution snapshot for {task_id}")
                return commit.hexsha
            return self.get_head_sha()
        except Exception:
            return self.get_head_sha()

    def rollback_to(self, checkpoint_sha: str) -> bool:
        """Revert working directory hard to the specified checkpoint SHA."""
        if not checkpoint_sha:
            return False
        repo = self._get_repo()
        try:
            repo.git.reset("--hard", checkpoint_sha)
            repo.git.clean("-fd")
            return True
        except Exception:
            return False

    def is_dirty(self) -> bool:
        """Check if workspace currently has uncommitted modifications."""
        repo = self._get_repo()
        return repo.is_dirty(untracked_files=True)

