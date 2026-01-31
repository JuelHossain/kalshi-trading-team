"""
Unit tests for HandAgent - Order execution and pre-trade validation.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from agents.hand import HandAgent
from core.vault import RecursiveVault


@pytest.fixture
def mock_bus():
    """Create a mock event bus."""
    bus = MagicMock()
    bus.publish = AsyncMock()
    return bus


@pytest.fixture
def mock_vault():
    """Create an initialized mock vault."""
    vault = MagicMock(spec=RecursiveVault)
    vault.current_balance = 50000  # $500
    vault.get_available_balance.return_value = 50000
    vault.kill_switch_active = False
    vault.reserve_funds.return_value = True
    vault.confirm_reservation = MagicMock()
    vault.release_reservation = MagicMock()
    return vault


@pytest.fixture
def hand_agent(mock_bus, mock_vault):
    """Create a HandAgent with mocked dependencies."""
    agent = HandAgent(
        agent_id=4,
        bus=mock_bus,
        vault=mock_vault,
        brain_agent=None,
        kalshi_client=None,  # Will use simulation mode
        synapse=None
    )
    return agent


class TestPreTradeValidation:
    """Test pre-trade validation logic."""

    @pytest.mark.asyncio
    async def test_rejects_when_kill_switch_active(self, hand_agent, mock_vault):
        """Order rejected when kill switch is active."""
        mock_vault.kill_switch_active = True

        result = await hand_agent.execute_order("KXWIN-2024-001", 50, 1000)

        assert result["success"] is False
        assert "kill switch" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_rejects_invalid_ticker(self, hand_agent):
        """Order rejected with invalid ticker format."""
        result = await hand_agent.execute_order("", 50, 1000)
        assert result["success"] is False
        assert "ticker" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_rejects_price_below_1_cent(self, hand_agent):
        """Order rejected when price is below 1 cent."""
        result = await hand_agent.execute_order("KXWIN-2024-001", 0, 1000)
        assert result["success"] is False
        assert "price" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_rejects_price_above_99_cents(self, hand_agent):
        """Order rejected when price is above 99 cents."""
        result = await hand_agent.execute_order("KXWIN-2024-001", 100, 1000)
        assert result["success"] is False
        assert "price" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_rejects_zero_stake(self, hand_agent):
        """Order rejected with zero stake."""
        result = await hand_agent.execute_order("KXWIN-2024-001", 50, 0)
        assert result["success"] is False
        assert "stake" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_rejects_negative_stake(self, hand_agent):
        """Order rejected with negative stake."""
        result = await hand_agent.execute_order("KXWIN-2024-001", 50, -100)
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_rejects_stake_above_maximum(self, hand_agent):
        """Order rejected when stake exceeds $75 maximum."""
        result = await hand_agent.execute_order("KXWIN-2024-001", 50, 8000)  # $80
        assert result["success"] is False
        assert "max" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_rejects_insufficient_funds(self, hand_agent, mock_vault):
        """Order rejected when available balance is insufficient."""
        mock_vault.get_available_balance.return_value = 500  # $5

        result = await hand_agent.execute_order("KXWIN-2024-001", 50, 1000)  # $10
        assert result["success"] is False
        assert "insufficient" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_rejects_below_hard_floor(self, hand_agent, mock_vault):
        """Order rejected when balance below $255 hard floor."""
        mock_vault.current_balance = 25000  # $250

        result = await hand_agent.execute_order("KXWIN-2024-001", 50, 1000)
        assert result["success"] is False
        assert "hard floor" in result["error"].lower()


class TestOrderExecution:
    """Test order execution flow."""

    @pytest.mark.asyncio
    async def test_simulation_mode_success(self, hand_agent, mock_vault):
        """Simulation mode returns success with proper reservation."""
        result = await hand_agent.execute_order("KXWIN-2024-001", 50, 1000)

        assert result["success"] is True
        assert result["simulated"] is True
        assert "order_id" in result
        mock_vault.reserve_funds.assert_called_once_with(1000)
        mock_vault.confirm_reservation.assert_called_once_with(1000)

    @pytest.mark.asyncio
    async def test_reservation_fails_if_cannot_reserve(self, hand_agent, mock_vault):
        """Order fails if fund reservation fails."""
        mock_vault.reserve_funds.return_value = False

        result = await hand_agent.execute_order("KXWIN-2024-001", 50, 1000)

        assert result["success"] is False
        assert "reserve" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_stake_too_small_for_price(self, hand_agent, mock_vault):
        """Order fails if stake can't buy at least 1 contract (live trading only)."""
        # stake=50, price=51 means 0 contracts
        # This validation only happens in live trading mode with a real client
        mock_client = AsyncMock()
        mock_client.place_order = AsyncMock(return_value={"order_id": "test-123"})
        hand_agent.kalshi_client = mock_client
        # Ensure vault has enough balance
        mock_vault.get_available_balance.return_value = 10000  # $100 available

        result = await hand_agent.execute_order("KXWIN-2024-001", 99, 50)

        assert result["success"] is False
        assert "too small" in result["error"].lower()


class TestKellyCriterion:
    """Test Kelly criterion stake calculation."""

    def test_zero_ev_returns_zero_stake(self, hand_agent):
        """Zero or negative EV returns zero stake."""
        stake = hand_agent.calculate_kelly_stake(confidence=0.6, ev=0)
        assert stake == 0

    def test_negative_ev_returns_zero_stake(self, hand_agent):
        """Negative EV returns zero stake."""
        stake = hand_agent.calculate_kelly_stake(confidence=0.6, ev=-0.1)
        assert stake == 0

    def test_high_confidence_higher_stake(self, hand_agent, mock_vault):
        """Higher confidence leads to higher stake."""
        mock_vault.current_balance = 10000
        mock_vault.get_available_balance = lambda: 10000

        low_conf_stake = hand_agent.calculate_kelly_stake(confidence=0.6, ev=0.1)
        high_conf_stake = hand_agent.calculate_kelly_stake(confidence=0.9, ev=0.1)

        assert high_conf_stake > low_conf_stake

    def test_stake_capped_at_max(self, hand_agent, mock_vault):
        """Stake never exceeds MAX_STAKE_CENTS."""
        mock_vault.current_balance = 1000000  # $10,000

        stake = hand_agent.calculate_kelly_stake(confidence=0.99, ev=0.5)

        assert stake <= hand_agent.MAX_STAKE_CENTS


class TestSnipeCheck:
    """Test snipe check logic."""

    @pytest.mark.asyncio
    async def test_snipe_check_validates_spread(self, hand_agent):
        """Snipe check fails when spread is too wide."""
        # Mock the kalshi_client to return wide spread
        mock_client = AsyncMock()
        mock_client.get_orderbook.return_value = {
            "bids": [{"price": 45}],
            "asks": [{"price": 60}]  # 15 cent spread
        }
        hand_agent.kalshi_client = mock_client

        result = await hand_agent.snipe_check("KXWIN-2024-001")

        assert result["valid"] is False
        assert "spread" in result["reason"].lower()

    @pytest.mark.asyncio
    async def test_snipe_check_passes_narrow_spread(self, hand_agent):
        """Snipe check passes when spread is narrow."""
        mock_client = AsyncMock()
        mock_client.get_orderbook.return_value = {
            "bids": [{"price": 48}],
            "asks": [{"price": 52}]  # 4 cent spread
        }
        hand_agent.kalshi_client = mock_client

        result = await hand_agent.snipe_check("KXWIN-2024-001")

        assert result["valid"] is True
        assert result["entry_price"] == 52

    @pytest.mark.asyncio
    async def test_snipe_check_no_client_simulates_success(self, hand_agent):
        """Without kalshi_client, snipe check simulates success."""
        hand_agent.kalshi_client = None

        result = await hand_agent.snipe_check("KXWIN-2024-001")

        assert result["valid"] is True
        assert result["entry_price"] == 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
