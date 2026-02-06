"""
Shared error handling helpers for Ghost Engine.
Provides consistent error handling patterns across all modules.
"""

from typing import Any, Callable, TypeVar
import functools
from core.display import log_error, AgentType

T = TypeVar("T")


def safe_execute(
    func: Callable[..., T],
    default_return: T = None,
    log_error: bool = True,
    error_message: str = "Operation failed"
) -> T:
    """
    Safely execute a function, catching and logging exceptions.

    Args:
        func: Function to execute
        default_return: Value to return on error
        log_error: Whether to log the error
        error_message: Custom error message for logging

    Returns:
        Function result or default_return on error
    """
    try:
        return func()
    except Exception as e:
        if log_error:
            log_error(f"{error_message}: {e}", AgentType.SOUL)
        return default_return


def async_safe_execute(
    func: Callable[..., T],
    default_return: T = None,
    log_error: bool = True,
    error_message: str = "Async operation failed"
) -> Callable[..., T]:
    """
    Decorator for async functions to safely execute and catch exceptions.

    Args:
        func: Async function to execute
        default_return: Value to return on error
        log_error: Whether to log the error
        error_message: Custom error message for logging

    Returns:
        Decorated async function
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs) -> T:
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            if log_error:
                log_error(f"{error_message}: {e}", AgentType.SOUL)
            return default_return
    return wrapper


def validate_required_fields(data: dict, required_fields: list[str]) -> tuple[bool, str | None]:
    """
    Validate that all required fields are present in a dictionary.

    Args:
        data: Dictionary to validate
        required_fields: List of required field names

    Returns:
        Tuple of (is_valid, error_message)
    """
    missing_fields = [field for field in required_fields if field not in data or data[field] is None]
    if missing_fields:
        return False, f"Missing required fields: {', '.join(missing_fields)}"
    return True, None


def validate_field_types(data: dict, field_types: dict[str, type]) -> tuple[bool, str | None]:
    """
    Validate that fields have the correct types.

    Args:
        data: Dictionary to validate
        field_types: Dictionary mapping field names to expected types

    Returns:
        Tuple of (is_valid, error_message)
    """
    for field, expected_type in field_types.items():
        if field in data and data[field] is not None:
            if not isinstance(data[field], expected_type):
                return False, f"Field '{field}' must be of type {expected_type.__name__}"
    return True, None


def validate_range(value: int, min_value: int, max_value: int, field_name: str = "value") -> tuple[bool, str | None]:
    """
    Validate that a value is within a specified range.

    Args:
        value: Value to validate
        min_value: Minimum allowed value (inclusive)
        max_value: Maximum allowed value (inclusive)
        field_name: Name of the field for error messages

    Returns:
        Tuple of (is_valid, error_message)
    """
    if value < min_value or value > max_value:
        return False, f"{field_name} must be between {min_value} and {max_value}"
    return True, None


__all__ = [
    "safe_execute",
    "async_safe_execute",
    "validate_required_fields",
    "validate_field_types",
    "validate_range",
]
