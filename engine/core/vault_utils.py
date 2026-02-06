"""
Shared Vault Utilities for Agents
Centralizes vault state broadcasting and common vault operations.
"""
from typing import Any

from core.bus import EventBus
from core.vault import RecursiveVault


async def publish_vault_state(
    bus: EventBus,
    vault: RecursiveVault,
    agent_name: str
):
    """
    Publish vault state to bus for UI consumption.

    Args:
        bus: EventBus instance
        vault: RecursiveVault instance
        agent_name: Name of the agent publishing the state
    """
    await bus.publish(
        "VAULT_UPDATE",
        {
            "principal": vault.PRINCIPAL_CAPITAL_CENTS / 100,
            "currentProfit": (vault.current_balance - vault.start_of_day_balance) / 100,
            "lockThreshold": vault.DAILY_PROFIT_THRESHOLD_CENTS / 100,
            "isLocked": vault.is_locked,
            "total": vault.current_balance / 100,
        },
        agent_name,
    )


def check_hard_floor_breach(vault: RecursiveVault) -> tuple[bool, str]:
    """
    Check if vault has breached the hard floor.

    Args:
        vault: RecursiveVault instance

    Returns:
        Tuple of (is_breached, error_message)
    """
    if vault.current_balance < vault.HARD_FLOOR_CENTS:
        balance_dollars = vault.current_balance / 100
        floor_dollars = vault.HARD_FLOOR_CENTS / 100
        return (
            True,
            f"Balance ${balance_dollars:.2f} below ${floor_dollars:.2f} floor. LOCKDOWN."
        )
    return (False, "")


def check_profit_lock_threshold(
    vault: RecursiveVault,
    threshold_cents: int
) -> tuple[bool, int]:
    """
    Check if profit threshold has been reached for locking principal.

    Args:
        vault: RecursiveVault instance
        threshold_cents: Profit threshold in cents

    Returns:
        Tuple of (should_lock, current_profit_cents)
    """
    current_profit = vault.current_balance - vault.start_of_day_balance
    should_lock = current_profit >= threshold_cents and not vault.is_locked
    return (should_lock, current_profit)
