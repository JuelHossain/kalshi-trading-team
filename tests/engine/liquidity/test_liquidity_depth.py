"""
Test suite for liquidity depth validation in HandAgent snipe_check.

This test reproduces slippage risks when order book has insufficient depth.
TDD Phase: RED - Tests should fail before the fix is implemented.
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock

import sys
sys.path.insert(0, 'e:/Projects/kalshi-trading-team')

from engine.agents.hand import HandAgent
from engine.core.bus import EventBus
from engine.core.vault import RecursiveVault
from engine.core.synapse import Synapse


@pytest.fixture
def mock_vault():
    """Create a mock vault with sufficient balance"""
    vault = MagicMock(spec=RecursiveVault)
    vault.current_balance = 30000  # $300
    vault.start_of_day_balance = 30000
    vault.is_locked = False
    vault.PRINCIPAL_CAPITAL_CENTS = 30000
    vault.DAILY_PROFIT_THRESHOLD_CENTS = 5000
    vault.kill_switch_active = False
    vault.reserve_funds = MagicMock(return_value=True)
    vault.confirm_reservation = MagicMock()
    vault.release_reservation = MagicMock()
    vault.get_available_balance = MagicMock(return_value=30000)
    return vault


@pytest.fixture
def mock_kalshi_client():
    """Create a mock Kalshi client"""
    client = AsyncMock()
    return client


@pytest.fixture
def hand_agent(mock_vault):
    """Create a HandAgent instance for testing"""
    bus = EventBus()
    synapse = None  # Not needed for snipe_check testing
    agent = HandAgent(
        agent_id=1,
        bus=bus,
        vault=mock_vault,
        synapse=synapse,
        kalshi_client=None
    )
    return agent


class TestLiquidityDepthValidation:
    """Test suite for liquidity depth validation in snipe_check"""

    @pytest.mark.asyncio
    async def test_snipe_check_insufficient_liquidity_best_ask(self, hand_agent, mock_kalshi_client):
        """
        TEST: Snipe check should fail when order book has insufficient liquidity
        at best price (less than 2x target stake)
        """
        hand_agent.kalshi_client = mock_kalshi_client

        # Mock orderbook with insufficient liquidity at best ask
        # Target stake would be ~$75, so we need less than $150 at best price
        mock_kalshi_client.get_orderbook = AsyncMock(return_value={
            "bids": [{"price": 45, "count": 1000}],  # $4500 liquidity on bid side
            "asks": [
                {"price": 50, "count": 100},  # Only $50 liquidity at best ask - INSUFFICIENT
                {"price": 51, "count": 1000},
            ]
        })

        result = await hand_agent.snipe_check("TEST-123")

        # Should reject due to insufficient liquidity depth
        assert result.get("valid") == False, "Should reject when liquidity depth < 2x target stake"
        assert "insufficient liquidity depth" in result.get("reason", "").lower(), \
            "Reason should mention insufficient liquidity"

    @pytest.mark.asyncio
    async def test_snipe_check_sufficient_liquidity_best_ask(self, hand_agent, mock_kalshi_client):
        """
        TEST: Snipe check should pass when order book has sufficient liquidity
        at best price (at least 2x target stake)
        """
        hand_agent.kalshi_client = mock_kalshi_client

        # Mock orderbook with sufficient liquidity at best ask
        # Target stake would be ~$75, so we need at least $150 at best price
        mock_kalshi_client.get_orderbook = AsyncMock(return_value={
            "bids": [{"price": 45, "count": 1000}],
            "asks": [
                {"price": 50, "count": 500},  # $250 liquidity at best ask - SUFFICIENT (> 2x $75)
                {"price": 51, "count": 1000},
            ]
        })

        result = await hand_agent.snipe_check("TEST-123")

        # Should accept when liquidity depth is sufficient
        assert result.get("valid") == True, "Should accept when liquidity depth >= 2x target stake"

    @pytest.mark.asyncio
    async def test_snipe_check_insufficient_liquidity_within_spread(self, hand_agent, mock_kalshi_client):
        """
        TEST: Snipe check should fail when cumulative liquidity within spread
        is less than 2x target stake
        """
        hand_agent.kalshi_client = mock_kalshi_client

        # Mock orderbook where best ask has low liquidity but next levels make up for it
        # Still insufficient overall within tight spread
        mock_kalshi_client.get_orderbook = AsyncMock(return_value={
            "bids": [{"price": 48, "count": 1000}],
            "asks": [
                {"price": 50, "count": 50},   # $25 at best ask
                {"price": 51, "count": 50},   # $25.50 at next level
                {"price": 52, "count": 50},   # $26 at third level
                # Total within 2 cent spread: ~$76.50 - still less than 2x ($150)
            ]
        })

        result = await hand_agent.snipe_check("TEST-123")

        # Should reject due to insufficient liquidity within spread
        assert result.get("valid") == False, "Should reject when cumulative liquidity within spread < 2x stake"

    @pytest.mark.asyncio
    async def test_snipe_check_no_liquidity_data(self, hand_agent, mock_kalshi_client):
        """
        TEST: Snipe check should handle missing liquidity data gracefully
        """
        hand_agent.kalshi_client = mock_kalshi_client

        # Mock orderbook with no asks
        mock_kalshi_client.get_orderbook = AsyncMock(return_value={
            "bids": [{"price": 45, "count": 1000}],
            "asks": []  # No asks available
        })

        result = await hand_agent.snipe_check("TEST-123")

        # Should reject when no liquidity data available
        assert result.get("valid") == False, "Should reject when no ask liquidity available"

    @pytest.mark.asyncio
    async def test_snipe_check_liquidity_within_spread_only(self, hand_agent, mock_kalshi_client):
        """
        TEST: Verify liquidity calculation only counts orders within the spread
        (best_bid to best_ask), not orders at higher prices
        """
        hand_agent.kalshi_client = mock_kalshi_client

        # Mock orderbook where spread is tight (48-50)
        # Only orders at price 50 are within the spread
        mock_kalshi_client.get_orderbook = AsyncMock(return_value={
            "bids": [{"price": 48, "count": 1000}],
            "asks": [
                {"price": 50, "count": 100},  # $50 at best ask - WITHIN spread
                {"price": 51, "count": 200},  # $102 - OUTSIDE spread (51 > 50)
                {"price": 52, "count": 100},  # $52 - OUTSIDE spread (52 > 50)
                # Within spread total: $50 < 2x $75 = $150 - INSUFFICIENT
            ]
        })

        result = await hand_agent.snipe_check("TEST-123")

        # Should reject because only $50 is within the spread (less than required $150)
        assert result.get("valid") == False, "Should reject when liquidity within spread < 2x stake"
        assert "insufficient liquidity depth" in result.get("reason", "").lower()

    @pytest.mark.asyncio
    async def test_snipe_check_wide_spread_still_rejected(self, hand_agent, mock_kalshi_client):
        """
        TEST: Even with sufficient liquidity, wide spread should still be rejected
        This verifies the new liquidity check doesn't bypass existing spread validation
        """
        hand_agent.kalshi_client = mock_kalshi_client

        # Mock orderbook with wide spread but sufficient liquidity
        mock_kalshi_client.get_orderbook = AsyncMock(return_value={
            "bids": [{"price": 40, "count": 1000}],  # Best bid: 40c
            "asks": [
                {"price": 50, "count": 1000},  # Best ask: 50c - 10 cent spread!
            ]
        })

        result = await hand_agent.snipe_check("TEST-123")

        # Should still reject due to wide spread (>5c)
        assert result.get("valid") == False, "Should reject on wide spread regardless of liquidity"
        assert "spread" in result.get("reason", "").lower(), "Reason should mention spread"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
