"""
Test Fix 1: Hard Floor Race Condition

Vulnerability: authorize_cycle() uses cached self.vault.current_balance which can be stale.
Fix: Read balance directly from DB source-of-truth via kalshi_client.get_balance().

This test demonstrates:
1. The vulnerability (BEFORE fix): Cached balance doesn't reflect external orders
2. The fix (AFTER): Direct DB read prevents hard floor bypass
"""

import pytest
import asyncio
import sys
import os
from pathlib import Path

# Add engine directory to path
engine_dir = Path(__file__).parent.parent.parent.parent / "engine"
sys.path.insert(0, str(engine_dir))

from unittest.mock import AsyncMock, MagicMock, patch
from main import GhostEngine


class TestHardFloorRaceCondition:
    """Test suite for hard floor race condition vulnerability"""

    @pytest.mark.asyncio
    async def test_vulnerability_stale_balance_allows_below_hard_floor(self):
        """
        VULNERABILITY TEST: Demonstrate that stale cached balance allows
        trading below hard floor when external orders are placed.

        Scenario:
        1. Vault has $300 (cached)
        2. External order fills, reducing balance to $200
        3. authorize_cycle() checks stale cache ($300) and approves
        4. System continues trading despite hard floor violation
        """
        engine = GhostEngine()
        engine.manual_kill_switch = False
        await engine.initialize_system()

        # Set vault with $300 (initial state) and disable kill switch
        await engine.vault.initialize(30000)  # $300 in cents
        engine.vault.kill_switch_active = False
        assert engine.vault.current_balance == 30000

        # Simulate external order that reduces balance to $200
        # This happens WITHOUT updating vault.current_balance (stale cache)
        real_balance_in_db = 20000  # $200 in cents

        # Mock kalshi_client.get_balance to return the REAL balance from DB
        with patch('main.kalshi_client') as mock_client:
            mock_client.get_balance = AsyncMock(return_value=real_balance_in_db)

            # Keep vault cache stale
            engine.vault.current_balance = 30000

            authorized = await engine.authorize_cycle()

            # AFTER FIX: Should return False because real balance ($200) < hard floor ($255)
            # BEFORE FIX: Would return True because stale cache ($300) >= hard floor
            assert authorized is False, \
                "Cycle should be rejected: real balance ($200) below hard floor ($255)"

    @pytest.mark.asyncio
    async def test_fix_direct_db_read_prevents_hard_floor_bypass(self):
        """
        FIX VERIFICATION: Verify that authorize_cycle() reads from kalshi_client
        instead of relying on stale cached balance.

        Scenario:
        1. Vault cache shows $300
        2. Real balance is $200 (external orders filled)
        3. authorize_cycle() should read real balance and reject cycle
        """
        engine = GhostEngine()
        engine.manual_kill_switch = False
        await engine.initialize_system()

        # Set up scenario: cache says $300, reality is $200
        await engine.vault.initialize(30000)
        engine.vault.kill_switch_active = False
        engine.vault.current_balance = 30000  # Stale cache

        real_balance = 20000  # Below hard floor

        with patch('main.kalshi_client') as mock_client:
            mock_client.get_balance = AsyncMock(return_value=real_balance)

            # Fix should prevent cycle from being authorized
            authorized = await engine.authorize_cycle()

            assert authorized is False, "Cycle should be rejected when real balance below hard floor"

            # Verify that get_balance was actually called (proves we're reading from DB)
            mock_client.get_balance.assert_called_once()

    @pytest.mark.asyncio
    async def test_sufficient_balance_with_stale_cache(self):
        """
        Verify that the fix doesn't break normal operation when balance is sufficient.

        Scenario:
        1. Vault cache shows $500
        2. Real balance is $450 (some orders filled, but still above hard floor)
        3. authorize_cycle() should still authorize the cycle
        """
        engine = GhostEngine()
        engine.manual_kill_switch = False
        await engine.initialize_system()

        await engine.vault.initialize(50000)
        engine.vault.kill_switch_active = False
        engine.vault.current_balance = 50000  # Slightly stale cache

        real_balance = 45000  # Still above hard floor ($255)

        with patch('main.kalshi_client') as mock_client:
            mock_client.get_balance = AsyncMock(return_value=real_balance)

            authorized = await engine.authorize_cycle()

            assert authorized is True, "Cycle should be authorized when balance above hard floor"

    @pytest.mark.asyncio
    async def test_exactly_at_hard_floor(self):
        """
        Edge case: Balance is exactly at hard floor ($255).

        The hard floor check uses `< 25500`, so $255 should still authorize.
        """
        engine = GhostEngine()
        engine.manual_kill_switch = False
        await engine.initialize_system()

        await engine.vault.initialize(25500)
        engine.vault.kill_switch_active = False

        real_balance = 25500  # Exactly $255 (hard floor threshold)

        with patch('main.kalshi_client') as mock_client:
            mock_client.get_balance = AsyncMock(return_value=real_balance)

            authorized = await engine.authorize_cycle()

            # $255 is NOT < $255, so it should authorize
            assert authorized is True, "Balance exactly at hard floor should authorize"

    @pytest.mark.asyncio
    async def test_one_cent_below_hard_floor(self):
        """
        Edge case: Balance is one cent below hard floor ($254.99).
        """
        engine = GhostEngine()
        engine.manual_kill_switch = False
        await engine.initialize_system()

        await engine.vault.initialize(25499)
        engine.vault.kill_switch_active = False

        real_balance = 25499  # $254.99 (one cent below hard floor)

        with patch('main.kalshi_client') as mock_client:
            mock_client.get_balance = AsyncMock(return_value=real_balance)

            authorized = await engine.authorize_cycle()

            # $254.99 IS < $255, so it should NOT authorize
            assert authorized is False, "Balance one cent below hard floor should not authorize"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
