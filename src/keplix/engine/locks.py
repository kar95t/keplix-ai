"""Subgraph concurrency write-locking for parallel agent workers."""

from datetime import datetime
import threading
from typing import Optional
import uuid

from keplix.engine.protocol import LockToken


class SubgraphLockError(Exception):
    """Raised when an agent attempts to acquire a lock on an already locked file."""
    pass


class SubgraphLockManager:
    """Thread-safe manager enforcing non-overlapping file write-locks across parallel agents."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._file_to_agent: dict[str, str] = {}
        self._tokens: dict[str, LockToken] = {}

    def acquire_lock(self, agent_id: str, file_paths: list[str]) -> Optional[LockToken]:
        """Attempt to acquire write-locks on the specified list of files.

        Returns a LockToken on success, or None if any file is already locked.
        """
        with self._lock:
            # Check for conflict
            for f in file_paths:
                existing_holder = self._file_to_agent.get(f)
                if existing_holder and existing_holder != agent_id:
                    return None

            token_id = str(uuid.uuid4())
            token = LockToken(
                token_id=token_id,
                agent_id=agent_id,
                locked_files=list(file_paths),
                acquired_at=datetime.utcnow(),
            )

            for f in file_paths:
                self._file_to_agent[f] = agent_id
            self._tokens[token_id] = token

            return token

    def release_lock(self, token: LockToken) -> bool:
        """Release the write-locks associated with the given LockToken."""
        with self._lock:
            if token.token_id not in self._tokens:
                return False

            for f in token.locked_files:
                if self._file_to_agent.get(f) == token.agent_id:
                    del self._file_to_agent[f]

            del self._tokens[token.token_id]
            return True

    def is_locked(self, file_path: str) -> bool:
        """Check if a specific file is currently write-locked."""
        with self._lock:
            return file_path in self._file_to_agent

    def get_holder(self, file_path: str) -> Optional[str]:
        """Return the agent ID holding a lock on the given file, if any."""
        with self._lock:
            return self._file_to_agent.get(file_path)

    def active_locks(self) -> dict[str, str]:
        """Return a copy of the active file -> agent mappings."""
        with self._lock:
            return dict(self._file_to_agent)

