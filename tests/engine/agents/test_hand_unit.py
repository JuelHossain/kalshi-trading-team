"""
Unit tests for HandAgent - Order execution and pre-trade validation.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from agents.hand import HandAgent
from core.constants import HARD_FLOOR_CENTS
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
    # spec= only exposes class attributes; HARD_FLOOR_CENTS is set in __init__.
    # Taken from the real constant so the mock cannot drift from production.
    vault.HARD_FLOOR_CENTS = HARD_FLOOR_CENTS
    vault.current_balance = 50000  # $500
    vault.get_available_balance.return_value = 50000
    # Derived from the values above, read at call time so tests that replace
    # get_available_balance or current_balance are still what sizing sees.
    # Not locked: tradeable is the available balance.
    vault.get_tradeable_balance.side_effect = lambda: vault.get_available_balance()
    vault.get_floor_headroom.side_effect = lambda: max(
        0, vault.current_balance - vault.HARD_FLOOR_CENTS
    )
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
        kalshi_client=None,  # tests that need one attach a mock explicitly
        synapse=None,
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
    async def test_successful_order_reserves_then_confirms(self, hand_agent, mock_vault):
        """A placed order reserves funds first, then confirms the reservation.

        This previously asserted a simulated success with no client attached.
        Simulation was removed from the trade path, so a missing client is now
        a refusal, not a fake fill.
        """
        mock_client = AsyncMock()
        mock_client.place_order = AsyncMock(return_value={"order_id": "test-123"})
        hand_agent.kalshi_client = mock_client

        result = await hand_agent.execute_order("KXWIN-2024-001", 50, 1000)

        assert result["success"] is True
        assert result["order_id"] == "test-123"
        mock_vault.reserve_funds.assert_called_once_with(1000)
        mock_vault.confirm_reservation.assert_called_once_with(1000)

    @pytest.mark.asyncio
    async def test_order_refused_without_a_client(self, hand_agent, mock_vault):
        """No market connection means no trade -- never a simulated fill."""
        hand_agent.kalshi_client = None

        result = await hand_agent.execute_order("KXWIN-2024-001", 50, 1000)

        assert result["success"] is False
        assert "unavailable" in result["error"].lower()
        mock_vault.reserve_funds.assert_not_called()
        mock_vault.confirm_reservation.assert_not_called()

    @pytest.mark.asyncio
    async def test_reservation_fails_if_cannot_reserve(self, hand_agent, mock_vault):
        """Order fails if fund reservation fails.

        The missing-client check runs before reservation, so a client is needed
        to reach this path at all.
        """
        mock_vault.reserve_funds.return_value = False
        hand_agent.kalshi_client = AsyncMock()

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
    """Stake is sized on edge, not on how certain the model claims to be.

    The previous implementation sized on `(confidence - 0.5) * 0.5 * 0.25` and
    used the edge only as an on/off gate, so two trades with identical
    confidence and wildly different edges received identical stakes. It also
    multiplied by `min(balance, max_stake)` rather than the bankroll, capping
    the result near 6% of the maximum -- the $75 ceiling was unreachable.
    """

    @staticmethod
    def _stake(hand_agent, probability, price_cents, confidence=0.9):
        return hand_agent.calculate_kelly_stake(
            confidence=confidence,
            ev=probability - price_cents / 100.0,
            probability=probability,
            price_cents=price_cents,
        )

    def test_zero_ev_returns_zero_stake(self, hand_agent):
        assert self._stake(hand_agent, probability=0.50, price_cents=50) == 0

    def test_negative_ev_returns_zero_stake(self, hand_agent):
        assert self._stake(hand_agent, probability=0.40, price_cents=50) == 0

    def test_bigger_edge_means_bigger_stake(self, hand_agent, mock_vault):
        """The property the old sizing could not express."""
        mock_vault.get_available_balance = lambda: 100_000

        small = self._stake(hand_agent, probability=0.55, price_cents=50)
        large = self._stake(hand_agent, probability=0.70, price_cents=50)

        assert 0 < small < large

    def test_confidence_does_not_change_the_stake(self, hand_agent, mock_vault):
        """Confidence is a gate, not a sizing input.

        The Brain already refuses anything below its threshold, so by the time
        the Hand sizes a trade, confidence has done its job.
        """
        mock_vault.get_available_balance = lambda: 100_000

        low = self._stake(hand_agent, probability=0.60, price_cents=50, confidence=0.86)
        high = self._stake(hand_agent, probability=0.60, price_cents=50, confidence=0.99)

        assert low == high

    def test_price_matters_at_the_same_probability(self, hand_agent, mock_vault):
        """Buying the same belief cheaper is a better bet and earns more size."""
        mock_vault.get_available_balance = lambda: 100_000

        cheap = self._stake(hand_agent, probability=0.70, price_cents=40)
        dear = self._stake(hand_agent, probability=0.70, price_cents=65)

        assert cheap > dear > 0

    def test_stake_capped_at_max(self, hand_agent, mock_vault):
        mock_vault.get_available_balance = lambda: 1_000_000  # $10,000

        stake = self._stake(hand_agent, probability=0.95, price_cents=50)

        assert stake == hand_agent.MAX_STAKE_CENTS

    def test_the_cap_is_actually_reachable(self, hand_agent, mock_vault):
        """The old sizing topped out near $4.68 against a $75 limit."""
        mock_vault.get_available_balance = lambda: 100_000

        stake = self._stake(hand_agent, probability=0.90, price_cents=50)

        assert stake == hand_agent.MAX_STAKE_CENTS

    def test_missing_inputs_refuse_rather_than_guess(self, hand_agent, mock_vault):
        """A wiring mistake must not silently produce a mis-sized live order."""
        mock_vault.get_available_balance = lambda: 100_000

        assert (
            hand_agent.calculate_kelly_stake(
                confidence=0.9, ev=0.2, probability=None, price_cents=50
            )
            == 0
        )
        assert (
            hand_agent.calculate_kelly_stake(
                confidence=0.9, ev=0.2, probability=0.7, price_cents=None
            )
            == 0
        )


class TestSnipeCheck:
    """Test snipe check logic."""

    @pytest.mark.asyncio
    async def test_snipe_check_validates_spread(self, hand_agent):
        """Snipe check fails when spread is too wide."""
        # Mock the kalshi_client to return wide spread
        mock_client = AsyncMock()
        mock_client.get_orderbook.return_value = {
            "bids": [{"price": 45}],
            "asks": [{"price": 60}],  # 15 cent spread
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
            "bids": [{"price": 48, "count": 300}],
            # 4 cent spread, and deep enough for the liquidity check: the book
            # must carry at least twice the max stake within the spread.
            "asks": [{"price": 52, "count": 300}],
        }
        hand_agent.kalshi_client = mock_client

        result = await hand_agent.snipe_check("KXWIN-2024-001")

        assert result["valid"] is True
        assert result["entry_price"] == 52

    @pytest.mark.asyncio
    async def test_snipe_check_refuses_without_a_client(self, hand_agent):
        """Without a client there is no order book, so the check must refuse.

        This previously asserted a simulated pass at a made-up entry price of
        50c -- approving a trade on data that was never fetched.
        """
        hand_agent.kalshi_client = None

        result = await hand_agent.snipe_check("KXWIN-2024-001")

        assert result["valid"] is False
        assert "unavailable" in result["reason"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
