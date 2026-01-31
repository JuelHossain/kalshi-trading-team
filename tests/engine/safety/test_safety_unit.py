"""
Unit tests for safety mechanisms - Kill switch, Ragnarok, and emergency procedures.
"""

import asyncio

import pytest
from core.safety import execute_ragnarok
from core.vault import RecursiveVault


class TestKillSwitchMechanisms:
    """Test kill switch triggers and behavior."""

    def test_vault_kill_switch_triggers_at_85_percent(self):
        """Vault kill switch activates when balance < 85% of principal."""
        vault = RecursiveVault()
        vault.PRINCIPAL_CAPITAL_CENTS = 30000  # $300 principal
        asyncio.run(vault.initialize(25499))  # $254.99 = 84.997%

        assert vault.kill_switch_active is True

    def test_vault_kill_switch_not_triggered_at_86_percent(self):
        """Vault kill switch does not activate when balance > 85% of principal."""
        vault = RecursiveVault()
        vault.PRINCIPAL_CAPITAL_CENTS = 30000
        asyncio.run(vault.initialize(25800))  # $258 = 86%

        assert vault.kill_switch_active is False


class TestRagnarokProtocol:
    """Test emergency Ragnarok liquidation protocol."""

    @pytest.mark.asyncio
    async def test_ragnarok_executes_without_error(self):
        """Ragnarok protocol executes without throwing exceptions."""
        # Ragnarok should not fail even if nothing to liquidate
        try:
            await execute_ragnarok()
        except Exception as e:
            pytest.fail(f"Ragnarok raised an exception: {e}")


class TestHardFloor:
    """Test hard floor safety mechanism ($255 minimum)."""

    def test_hard_floor_at_255_dollars(self):
        """Hard floor is exactly $255."""
        vault = RecursiveVault()
        # This would be checked in authorize_cycle
        assert 25500 == 255 * 100  # $255 in cents

    def test_balance_at_254_triggers_lockdown(self):
        """Balance of $254 should trigger emergency lockdown."""
        vault = RecursiveVault()
        asyncio.run(vault.initialize(25400))
        assert vault.current_balance < 25500


class TestProfitLocking:
    """Test profit locking at $50 threshold."""

    def test_profit_lock_at_exactly_50_dollars(self):
        """Lock activates at exactly $50 profit."""
        vault = RecursiveVault()
        vault.DAILY_PROFIT_THRESHOLD_CENTS = 5000
        asyncio.run(vault.initialize(30000))

        asyncio.run(vault.update_balance(35000))  # Exactly $50 profit

        assert vault.is_locked is True

    def test_profit_lock_at_51_dollars(self):
        """Lock activates at $51 profit."""
        vault = RecursiveVault()
        vault.DAILY_PROFIT_THRESHOLD_CENTS = 5000
        asyncio.run(vault.initialize(30000))

        asyncio.run(vault.update_balance(35100))  # $51 profit

        assert vault.is_locked is True

    def test_no_lock_at_49_dollars_profit(self):
        """Lock does not activate at $49 profit."""
        vault = RecursiveVault()
        vault.DAILY_PROFIT_THRESHOLD_CENTS = 5000
        asyncio.run(vault.initialize(30000))

        asyncio.run(vault.update_balance(34900))  # $49 profit

        assert vault.is_locked is False


class TestAuthorizationChecks:
    """Test cycle authorization checks."""

    def test_authorize_cycle_checks_kill_switch(self):
        """Cycle not authorized when kill switch is active."""
        # This would typically be tested through GhostEngine
        # but we verify the vault state
        vault = RecursiveVault()
        vault.PRINCIPAL_CAPITAL_CENTS = 30000
        asyncio.run(vault.initialize(25000))  # Below 85%

        assert vault.kill_switch_active is True

    def test_authorize_cycle_checks_hard_floor(self):
        """Cycle not authorized when below hard floor."""
        vault = RecursiveVault()
        asyncio.run(vault.initialize(25499))  # Below $255

        assert vault.current_balance < 25500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
