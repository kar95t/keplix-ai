"""Silent OpenTelemetry and Langfuse callback tracer."""

import os
from typing import Any, Optional


def get_langfuse_callback(session_id: Optional[str] = None) -> Optional[Any]:
    """Initialize Langfuse CallbackHandler silently if environment credentials are present.

    Returns None if Langfuse is unconfigured or not installed.
    """
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")

    if not (public_key and secret_key):
        return None

    try:
        from langfuse.callback import CallbackHandler

        host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
        return CallbackHandler(
            public_key=public_key,
            secret_key=secret_key,
            host=host,
            session_id=session_id,
        )
    except ImportError:
        return None
    except Exception:
        return None

