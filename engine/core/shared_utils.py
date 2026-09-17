"""
Shared utility functions for Ghost Engine core modules.
This module consolidates common patterns used across multiple files.
"""

import asyncio
import os
import sqlite3
import time
from collections.abc import Callable
from datetime import datetime
from functools import wraps
from typing import TypeVar

# -------------------------------------------------------------------------
# Database Utilities
# -------------------------------------------------------------------------

T = TypeVar("T")


def retry_sqlite(max_retries: int = 3, base_delay: float = 0.05):
    """
    Retry decorator for SQLite operations that may encounter locked database.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay for exponential backoff in seconds

    Returns:
        Decorated function with retry logic
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        """Wrap `func` with the retry loop configured by retry_sqlite."""

        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            """Retry on sqlite3.OperationalError (a locked database) with backoff."""
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except sqlite3.OperationalError as e:
                    if "locked" in str(e).lower() and attempt < max_retries - 1:
                        # Exponential backoff
                        delay = base_delay * (2**attempt)
                        time.sleep(delay)
                        continue
                    # Re-raise if not locked error or retries exhausted
                    raise
            return None

        return wrapper

    return decorator


async def run_in_executor(func: Callable[..., T], *args, **kwargs) -> T:
    """
    Run a synchronous function in an executor to avoid blocking the event loop.

    Args:
        func: The function to execute
        *args: Positional arguments for the function
        **kwargs: Keyword arguments for the function

    Returns:
        The result of the function
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, func, *args, **kwargs)


# -------------------------------------------------------------------------
# Validation Utilities
# -------------------------------------------------------------------------


def validate_positive_amount(amount: int) -> bool:
    """
    Validate that an amount is positive.

    Args:
        amount: The amount to validate

    Returns:
        True if amount is positive, False otherwise
    """
    return amount > 0


def validate_amount_not_exceeding(amount: int, maximum: int) -> bool:
    """
    Validate that an amount does not exceed a maximum.

    Args:
        amount: The amount to validate
        maximum: The maximum allowed value

    Returns:
        True if amount is less than or equal to maximum, False otherwise
    """
    return amount <= maximum


# -------------------------------------------------------------------------
# Time Utilities
# -------------------------------------------------------------------------


def get_current_timestamp() -> str:
    """
    Get current timestamp in ISO format.

    Returns:
        Current timestamp as ISO format string
    """
    return datetime.now().isoformat()


def get_current_unix_timestamp() -> float:
    """
    Get current Unix timestamp.

    Returns:
        Current Unix timestamp as float
    """
    return time.time()


# -------------------------------------------------------------------------
# Async Utilities
# -------------------------------------------------------------------------


async def gather_with_exceptions(*tasks, return_exceptions: bool = False):
    """
    Gather tasks with better exception handling.

    Args:
        *tasks: Async tasks to gather
        return_exceptions: If True, exceptions are returned as results

    Returns:
        List of results or exceptions
    """
    return await asyncio.gather(*tasks, return_exceptions=return_exceptions)


# -------------------------------------------------------------------------
# Environment Utilities
# -------------------------------------------------------------------------


def get_env_bool(key: str, default: bool = False) -> bool:
    """
    Get boolean value from environment variable.

    Args:
        key: Environment variable name
        default: Default value if not set

    Returns:
        Boolean value from environment
    """
    value = os.getenv(key, "").lower()
    if value in ("true", "1", "yes", "on"):
        return True
    if value in ("false", "0", "no", "off"):
        return False
    return default


def get_env_int(key: str, default: int = 0) -> int:
    """
    Get integer value from environment variable.

    Args:
        key: Environment variable name
        default: Default value if not set or invalid

    Returns:
        Integer value from environment
    """
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default


def get_env_float(key: str, default: float = 0.0) -> float:
    """
    Get float value from environment variable.

    Args:
        key: Environment variable name
        default: Default value if not set or invalid

    Returns:
        Float value from environment
    """
    try:
        return float(os.getenv(key, str(default)))
    except ValueError:
        return default


# -------------------------------------------------------------------------
# String Utilities
# -------------------------------------------------------------------------


def truncate_string(s: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate a string to a maximum length.

    Args:
        s: The string to truncate
        max_length: Maximum length of the result
        suffix: Suffix to add if truncated

    Returns:
        Truncated string
    """
    if len(s) <= max_length:
        return s
    return s[: max_length - len(suffix)] + suffix


def format_cents_to_dollars(cents: int, show_symbol: bool = True) -> str:
    """
    Format cents to dollar string.

    Args:
        cents: Amount in cents
        show_symbol: Whether to include dollar symbol

    Returns:
        Formatted dollar string
    """
    dollars = cents / 100
    result = f"{dollars:.2f}"
    return f"${result}" if show_symbol else result


def format_dollars_to_cents(dollars: float) -> int:
    """
    Convert dollars to cents.

    Args:
        dollars: Amount in dollars

    Returns:
        Amount in cents
    """
    return int(dollars * 100)


__all__ = [
    "format_cents_to_dollars",
    "format_dollars_to_cents",
    "gather_with_exceptions",
    "get_current_timestamp",
    "get_current_unix_timestamp",
    "get_env_bool",
    "get_env_float",
    "get_env_int",
    "retry_sqlite",
    "run_in_executor",
    "truncate_string",
    "validate_amount_not_exceeding",
    "validate_positive_amount",
]


# -------------------------------------------------------------------------
# Async Scheduling Utilities
# -------------------------------------------------------------------------


# Tasks scheduled by fire_and_forget. asyncio holds only a weak reference to
# a running task; without a strong one here it can be garbage-collected
# mid-flight and the coroutine simply stops. Entries remove themselves when
# done.
_background_tasks: set[asyncio.Task] = set()


def fire_and_forget(coro) -> None:
    """Run a fire-and-forget coroutine from sync or async context.

    `asyncio.create_task` needs a running loop and raises RuntimeError without
    one. Sync helpers that log via an async callback therefore crash when called
    outside the event loop -- and because those calls sit on degraded paths
    ("API key missing", "init failed"), the recovery path fails instead of the
    condition it was reporting.

    Schedules the coroutine when a loop is running, otherwise runs it to
    completion on a temporary one. Logging must never take down its caller, so
    a failure here is swallowed after closing the coroutine.
    """
    try:
        task = asyncio.get_running_loop().create_task(coro)
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)
    except RuntimeError:
        try:
            asyncio.run(coro)
        except Exception:
            coro.close()
