"""Stack-trace compressor and secret redaction filter for agent context windows."""

import re
from typing import Optional

SECRET_PATTERNS = [
    # Generic API Keys / Bearer tokens
    (re.compile(r"(Bearer\s+)[A-Za-z0-9_\-\.]{16,}", re.IGNORECASE), r"\1[REDACTED_TOKEN]"),
    (re.compile(r"(sk-[a-zA-Z0-9_\-]{20,})"), "[REDACTED_API_KEY]"),
    (re.compile(r"(ghp_[a-zA-Z0-9]{30,})"), "[REDACTED_GITHUB_TOKEN]"),
    (re.compile(r"(AKIA[0-9A-Z]{16})"), "[REDACTED_AWS_KEY]"),
    # Key-value secret assignments in traces/logs
    (
        re.compile(r"((?:api[_-]?key|secret|password|token)\s*[:=]\s*['\"]?)([^'\"\s\n]{8,})(['\"]?)", re.IGNORECASE),
        r"\1[REDACTED]\3",
    ),
]


class LogPruner:
    """Filters sensitive tokens and compresses verbose stack traces to preserve LLM token context."""

    def __init__(self, max_lines: int = 40) -> None:
        self.max_lines = max_lines

    def redact_secrets(self, text: str) -> str:
        """Strip known API keys, credentials, and tokens from log strings."""
        redacted = text
        for pattern, replacement in SECRET_PATTERNS:
            redacted = pattern.sub(replacement, redacted)
        return redacted

    def compress_stacktrace(self, trace_text: str, max_lines: Optional[int] = None) -> str:
        """Compress lengthy repetitive stack traces, keeping relevant leading and trailing frames."""
        limit = max_lines or self.max_lines
        lines = trace_text.splitlines()

        if len(lines) <= limit:
            return trace_text

        # Keep initial context + final error details
        head_count = limit // 2
        tail_count = limit - head_count - 1
        skipped = len(lines) - (head_count + tail_count)

        compressed = (
            lines[:head_count]
            + [f"... [{skipped} verbose framework stack trace lines pruned for brevity] ..."]
            + lines[-tail_count:]
        )
        return "\n".join(compressed)

    def process(self, raw_text: str) -> str:
        """Apply redaction followed by stack trace compression."""
        cleaned = self.redact_secrets(raw_text)
        return self.compress_stacktrace(cleaned)

