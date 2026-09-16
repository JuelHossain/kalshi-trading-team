"""The engine must not stack into a market it already holds.

Nothing stopped the same ticker being scanned, approved and bought on cycle
after cycle. With no position tracking and no exit path, exposure accumulated
in a holding the engine could neither see nor close.
"""

from unittest.mock import AsyncMock

import pytest

from agents.hand.execution import has_open_position

# Fixtures and helpers shared with the trade-cycle tests.
from tests.engine.integration.test_trade_cycle import _debate, _opportunity, cycle  # noqa: F401


@pytest.fixture
def client():
    c = AsyncMock()
    c.get_positions = AsyncMock(return_value=[])
    return c


class TestHasOpenPosition:
    @pytest.mark.asyncio
    async def test_a_held_market_is_reported(self, client):
        client.get_positions = AsyncMock(return_value=[{"ticker": "KXA", "position": 10}])
        assert await has_open_position(client, "KXA") is True

    @pytest.mark.asyncio
    async def test_an_unheld_market_is_free_to_trade(self, client):
        client.get_positions = AsyncMock(return_value=[{"ticker": "KXB", "position": 10}])
        assert await has_open_position(client, "KXA") is False

    @pytest.mark.asyncio
    async def test_a_flat_market_is_not_a_holding(self, client):
        client.get_positions = AsyncMock(return_value=[{"ticker": "KXA", "position": 0}])
        assert await has_open_position(client, "KXA") is False

    @pytest.mark.asyncio
    async def test_a_short_holding_still_counts(self, client):
        client.get_positions = AsyncMock(return_value=[{"ticker": "KXA", "position": -7}])
        assert await has_open_position(client, "KXA") is True

    @pytest.mark.asyncio
    async def test_unreadable_positions_fail_closed(self, client):
        """Declining a good trade costs an opportunity. Doubling blindly costs money."""
        client.get_positions = AsyncMock(side_effect=RuntimeError("API down"))
        assert await has_open_position(client, "KXA") is True


class TestTheHandRefusesToStack:
    @pytest.mark.asyncio
    async def test_no_order_is_placed_for_a_market_already_held(self, cycle):
        cycle["kalshi"].get_positions = AsyncMock(
            return_value=[{"ticker": "KXTEST-01", "position": 10}]
        )
        await cycle["vault"].initialize(100_000)

        cycle["brain"].run_debate = _debate()
        await cycle["brain"].process_single_opportunity(_opportunity())
        await cycle["hand"].on_execution_ready(None)

        cycle["kalshi"].place_order.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_an_unheld_market_still_trades(self, cycle):
        """The guard must not block everything."""
        cycle["kalshi"].get_positions = AsyncMock(return_value=[])
        await cycle["vault"].initialize(100_000)

        cycle["brain"].run_debate = _debate()
        await cycle["brain"].process_single_opportunity(_opportunity())
        await cycle["hand"].on_execution_ready(None)

        cycle["kalshi"].place_order.assert_awaited_once()
