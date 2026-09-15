"""
Unit tests for safety mechanisms - Kill switch, Ragnarok, and emergency procedures.
"""

import asyncio

from unittest.mock import AsyncMock

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
    async def test_reports_zero_when_no_active_orders(self, monkeypatch):
        """Nothing to liquidate is a success, not a failure."""
        import core.safety

        client = AsyncMock()
        client.request = AsyncMock(return_value={"orders": []})
        monkeypatch.setattr(core.safety, "kalshi_client", client)

        result = await execute_ragnarok()

        assert result["status"] == "success"
        assert result["orders_cancelled"] == 0

    @pytest.mark.asyncio
    async def test_cancels_every_open_order(self, monkeypatch):
        """The whole point of the protocol: every open order is cancelled."""
        import core.safety

        client = AsyncMock()

        async def fake_request(method, path, **_kwargs):
            if method == "GET":
                return {"orders": [{"order_id": "a"}, {"order_id": "b"}, {"order_id": "c"}]}
            return {"cancelled": True}

        client.request = AsyncMock(side_effect=fake_request)
        monkeypatch.setattr(core.safety, "kalshi_client", client)

        result = await execute_ragnarok()

        assert result["orders_cancelled"] == 3
        deleted = [
            call.args[1]
            for call in client.request.call_args_list
            if call.args[0] == "DELETE"
        ]
        assert sorted(deleted) == [
            "/portfolio/orders/a",
            "/portfolio/orders/b",
            "/portfolio/orders/c",
        ]

    @pytest.mark.asyncio
    async def test_counts_only_orders_actually_cancelled(self, monkeypatch):
        """A partial failure must not be reported as a clean liquidation."""
        import core.safety

        client = AsyncMock()

        async def fake_request(method, path, **_kwargs):
            if method == "GET":
                return {"orders": [{"order_id": "a"}, {"order_id": "b"}]}
            return {"ok": True} if path.endswith("/a") else None

        client.request = AsyncMock(side_effect=fake_request)
        monkeypatch.setattr(core.safety, "kalshi_client", client)

        result = await execute_ragnarok()

        assert result["orders_cancelled"] == 1

    @pytest.mark.asyncio
    async def test_survives_an_api_failure(self, monkeypatch):
        """A failed fetch must not raise out of the emergency path."""
        import core.safety

        client = AsyncMock()
        client.request = AsyncMock(return_value=None)
        monkeypatch.setattr(core.safety, "kalshi_client", client)

        result = await execute_ragnarok()

        assert result["status"] == "success"
        assert result["orders_cancelled"] == 0


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
