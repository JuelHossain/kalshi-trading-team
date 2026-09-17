"""
Flow control utilities for queue management.
Provides centralized checks to prevent system overload.
"""

from typing import TYPE_CHECKING

from core.constants import (
    MAX_EXECUTION_QUEUE_SIZE,
    MAX_OPPORTUNITY_QUEUE_SIZE,
    RESTOCK_COOLDOWN_SECONDS,
    RESTOCK_THRESHOLD_VETO_COUNT,
)

if TYPE_CHECKING:
    from core.synapse import Synapse


# ==============================================================================
# FLOW CONTROL CHECKS
# ==============================================================================


async def check_execution_queue_limit(
    synapse: "Synapse", limit: int = MAX_EXECUTION_QUEUE_SIZE
) -> tuple[bool, int]:
    """
    Check if execution queue is at limit.

    Args:
        synapse: The Synapse instance
        limit: Maximum queue size (default: MAX_EXECUTION_QUEUE_SIZE)

    Returns:
        Tuple of (is_at_limit, current_size)
    """
    if not synapse:
        return False, 0

    current_size = await synapse.executions.size()
    is_at_limit = current_size >= limit

    return is_at_limit, current_size


async def check_opportunity_queue_limit(
    synapse: "Synapse", limit: int = MAX_OPPORTUNITY_QUEUE_SIZE
) -> tuple[bool, int]:
    """
    Check if opportunity queue is at limit.

    Args:
        synapse: The Synapse instance
        limit: Maximum queue size (default: MAX_OPPORTUNITY_QUEUE_SIZE)

    Returns:
        Tuple of (is_at_limit, current_size)
    """
    if not synapse:
        return False, 0

    current_size = await synapse.opportunities.size()
    is_at_limit = current_size >= limit

    return is_at_limit, current_size


async def should_pause_processing(synapse: "Synapse") -> bool:
    """
    Determine if processing should pause due to queue limits.

    Args:
        synapse: The Synapse instance

    Returns:
        True if processing should pause, False otherwise
    """
    exec_at_limit, _ = await check_execution_queue_limit(synapse)
    return exec_at_limit


async def should_restock(
    synapse: "Synapse",
    dumped_count: int,
    last_restock_time: float,
    current_time: float,
    veto_threshold: int = RESTOCK_THRESHOLD_VETO_COUNT,
    cooldown_seconds: int = RESTOCK_COOLDOWN_SECONDS,
) -> bool:
    """
    Determine if a restock should be requested from Senses.

    Args:
        synapse: The Synapse instance
        dumped_count: Number of opportunities vetoed since last restock
        last_restock_time: Unix timestamp of last restock
        current_time: Current Unix timestamp
        veto_threshold: Minimum vetoes before restock (default: RESTOCK_THRESHOLD_VETO_COUNT)
        cooldown_seconds: Minimum seconds between restocks (default: RESTOCK_COOLDOWN_SECONDS)

    Returns:
        True if restock should be requested, False otherwise
    """
    # Check veto count threshold
    if dumped_count < veto_threshold:
        return False

    # Check execution queue limit - don't restock if full
    exec_at_limit, _ = await check_execution_queue_limit(synapse)
    if exec_at_limit:
        return False

    # Check cooldown
    time_since_restock = current_time - last_restock_time
    return not time_since_restock < cooldown_seconds
