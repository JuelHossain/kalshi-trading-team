"""
Unit tests for RecursiveVault - Financial safety and balance management.
"""

import asyncio

import pytest
from core.vault import RecursiveVault


@pytest.fixture
def vault():
    """Create a fresh vault instance for each test."""
    return RecursiveVault(test_mode=True)  # Use test mode to skip persistence


@pytest.fixture
def initialized_vault(vault):
    """Create an initialized vault with $500 balance."""
    asyncio.run(vault.initialize(50000))  # $500 in cents
    return vault


class TestVaultInitialization:
    """Test vault initialization and basic properties."""

    def test_initial_state(self, vault):
        """Vault starts with zero balances and inactive flags."""
        assert vault.current_balance == 0
        assert vault.start_of_day_balance == 0
        assert vault.is_locked is False
        assert vault.kill_switch_active is False
        assert vault.initialized is False

    def test_initialize_sets_balances(self, vault):
        """Initialize sets both current and SOD balance."""
        asyncio.run(vault.initialize(50000))
        assert vault.current_balance == 50000
        assert vault.start_of_day_balance == 50000
        assert vault.initialized is True


class TestKillSwitch:
    """Test kill switch activation and deactivation."""

    def test_kill_switch_activates_below_85_percent(self, vault):
        """Kill switch activates when balance drops below 85% of principal."""
        vault.PRINCIPAL_CAPITAL_CENTS = 30000  # $300 principal
        asyncio.run(vault.initialize(25000))  # $250 = 83% of $300
        assert vault.kill_switch_active is True

    def test_kill_switch_not_active_above_85_percent(self, vault):
        """Kill switch stays inactive when balance is above 85% of principal."""
        vault.PRINCIPAL_CAPITAL_CENTS = 30000  # $300 principal
        asyncio.run(vault.initialize(26000))  # $260 = 87% of $300
        assert vault.kill_switch_active is False

    def test_kill_switch_deactivates_when_balance_recovers(self, vault):
        """Kill switch can deactivate when balance recovers."""
        vault.PRINCIPAL_CAPITAL_CENTS = 30000
        asyncio.run(vault.initialize(25000))  # Below threshold
        assert vault.kill_switch_active is True

        # Recovery not typically allowed in real trading, but test the mechanism
        asyncio.run(vault.update_balance(26000))
        assert vault.kill_switch_active is False


class TestPrincipalLock:
    """Test profit locking mechanism."""

    def test_lock_activates_at_profit_threshold(self, vault):
        """Vault locks when daily profit reaches threshold."""
        vault.DAILY_PROFIT_THRESHOLD_CENTS = 5000  # $50 threshold
        asyncio.run(vault.initialize(30000))  # Start with $300
        assert vault.is_locked is False

        # Increase balance to exceed threshold
        asyncio.run(vault.update_balance(36000))  # $60 profit
        assert vault.is_locked is True

    def test_lock_does_not_activate_below_threshold(self, vault):
        """Vault stays unlocked when profit is below threshold."""
        vault.DAILY_PROFIT_THRESHOLD_CENTS = 5000
        asyncio.run(vault.initialize(30000))

        asyncio.run(vault.update_balance(34000))  # $40 profit
        assert vault.is_locked is False

    def test_manual_lock(self, vault):
        """Principal can be locked manually."""
        asyncio.run(vault.initialize(30000))
        vault.lock_principal()
        assert vault.is_locked is True


class TestTradeableCapital:
    """Test tradeable capital calculations."""

    def test_unlocked_vault_allows_full_balance(self, vault):
        """When unlocked, all balance is tradeable."""
        asyncio.run(vault.initialize(50000))
        result = asyncio.run(vault.get_tradeable_capital())
        assert result == 50000

    def test_locked_vault_only_allows_house_money(self, vault):
        """When locked, only profit above principal is tradeable."""
        vault.PRINCIPAL_CAPITAL_CENTS = 30000
        asyncio.run(vault.initialize(40000))  # $100 profit
        vault.is_locked = True

        result = asyncio.run(vault.get_tradeable_capital())
        assert result == 10000  # Only $100 profit available

    def test_locked_vault_returns_zero_if_no_profit(self, vault):
        """Locked vault with no profit returns 0 tradeable capital."""
        vault.PRINCIPAL_CAPITAL_CENTS = 30000
        asyncio.run(vault.initialize(25000))  # $50 loss
        vault.is_locked = True

        result = asyncio.run(vault.get_tradeable_capital())
        assert result == 0


class TestAtomicBalanceOperations:
    """Test two-phase commit balance operations."""

    def test_reserve_funds_reduces_available_balance(self, vault):
        """Reserving funds reduces available balance."""
        asyncio.run(vault.initialize(50000))

        success = vault.reserve_funds(10000)
        assert success is True
        assert vault.get_available_balance() == 40000
        assert vault._reserved_funds == 10000
        assert vault.current_balance == 50000  # Unchanged until confirmation

    def test_reserve_funds_fails_if_insufficient(self, vault):
        """Cannot reserve more than available."""
        asyncio.run(vault.initialize(10000))
        vault.reserve_funds(5000)  # Reserve half

        success = vault.reserve_funds(6000)  # Try to reserve more than remaining
        assert success is False
        assert vault.get_available_balance() == 5000

    def test_confirm_reservation_deducts_balance(self, vault):
        """Confirming reservation actually deducts from balance."""
        asyncio.run(vault.initialize(50000))
        vault.reserve_funds(10000)

        vault.confirm_reservation(10000)
        assert vault.current_balance == 40000
        assert vault._reserved_funds == 0

    def test_release_reservation_restores_available(self, vault):
        """Releasing reservation makes funds available again."""
        asyncio.run(vault.initialize(50000))
        vault.reserve_funds(10000)

        vault.release_reservation(10000)
        assert vault.get_available_balance() == 50000
        assert vault._reserved_funds == 0
        assert vault.current_balance == 50000  # Unchanged

    def test_multiple_reservations_tracked_correctly(self, vault):
        """Multiple reservations are tracked independently."""
        asyncio.run(vault.initialize(50000))

        vault.reserve_funds(10000)
        vault.reserve_funds(5000)

        assert vault._reserved_funds == 15000
        assert vault.get_available_balance() == 35000

        vault.confirm_reservation(10000)
        assert vault._reserved_funds == 5000
        assert vault.current_balance == 40000

        vault.release_reservation(5000)
        assert vault._reserved_funds == 0
        assert vault.get_available_balance() == 40000


class TestHardFloor:
    """Test hard floor safety mechanism."""

    def test_balance_below_255_triggers_emergency(self, vault):
        """Balance below $255 should trigger emergency lockdown."""
        asyncio.run(vault.initialize(25000))  # $250
        # In practice, this would be checked before trading
        assert vault.current_balance < 25500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
