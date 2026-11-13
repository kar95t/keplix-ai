"""SQLite persistence checkpointer for LangGraph state persistence (.keplix/state.db)."""

from contextlib import contextmanager
from pathlib import Path
import sqlite3
from typing import Generator

try:
    from langgraph.checkpoint.sqlite import SqliteSaver
except ImportError:
    SqliteSaver = None  # type: ignore[assignment,misc]


def get_default_db_path(state_dir: str = ".keplix") -> Path:
    """Return the absolute path to the local SQLite state database."""
    base_dir = Path(state_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir / "state.db"


@contextmanager
def get_sqlite_checkpointer(
    db_path: Path | None = None,
) -> Generator[SqliteSaver | sqlite3.Connection | None, None, None]:
    """Provide a thread-safe SQLite checkpointer context manager for LangGraph graphs."""
    target_path = db_path or get_default_db_path()

    if SqliteSaver is not None:
        with SqliteSaver.from_conn_string(str(target_path)) as checkpointer:
            yield checkpointer
    else:
        # Fallback raw SQLite connection for lightweight mock/local usage
        conn = sqlite3.connect(str(target_path))
        try:
            yield conn
        finally:
            conn.close()

