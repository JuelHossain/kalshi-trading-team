"""
Shared display utilities for Ghost Engine.
Provides consistent console output formatting across all modules.
"""

from typing import Any
from datetime import datetime


def format_timestamp(ts: str | datetime | None = None) -> str:
    """
    Format a timestamp for display.

    Args:
        ts: Timestamp (string, datetime, or None for current time)

    Returns:
        Formatted timestamp string
    """
    if ts is None:
        ts = datetime.now()
    elif isinstance(ts, str):
        return ts  # Already formatted
    return ts.isoformat()


def format_log_message(
    agent: str,
    level: str,
    message: str,
    context: dict[str, Any] | None = None
) -> str:
    """
    Format a log message consistently.

    Args:
        agent: Agent name
        level: Log level (INFO, WARNING, ERROR, etc.)
        message: Log message
        context: Optional context dictionary

    Returns:
        Formatted log message
    """
    parts = [f"[{agent}]", f"[{level}]", message]
    if context:
        context_str = ", ".join(f"{k}={v}" for k, v in context.items())
        parts.append(f"| Context: {context_str}")
    return " ".join(parts)


def format_error_message(
    agent: str,
    code: str,
    message: str,
    hint: str | None = None
) -> str:
    """
    Format an error message consistently.

    Args:
        agent: Agent name
        code: Error code
        message: Error message
        hint: Optional hint for resolution

    Returns:
        Formatted error message
    """
    parts = [f"[{agent}]", f"[ERROR]", f"{code}: {message}"]
    if hint:
        parts.append(f"| Hint: {hint}")
    return " ".join(parts)


def format_success_message(agent: str, message: str) -> str:
    """
    Format a success message consistently.

    Args:
        agent: Agent name
        message: Success message

    Returns:
        Formatted success message
    """
    return f"[{agent}] [SUCCESS] {message}"


def format_warning_message(agent: str, message: str) -> str:
    """
    Format a warning message consistently.

    Args:
        agent: Agent name
        message: Warning message

    Returns:
        Formatted warning message
    """
    return f"[{agent}] [WARNING] {message}"


def format_debug_message(agent: str, message: str) -> str:
    """
    Format a debug message consistently.

    Args:
        agent: Agent name
        message: Debug message

    Returns:
        Formatted debug message
    """
    return f"[{agent}] [DEBUG] {message}"


__all__ = [
    "format_timestamp",
    "format_log_message",
    "format_error_message",
    "format_success_message",
    "format_warning_message",
    "format_debug_message",
]
