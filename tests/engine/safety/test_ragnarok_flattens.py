"""Ragnarok must reduce exposure, not just tidy the order book.

The protocol cancelled resting orders and stopped. A filled order is a
position, and nothing in the engine could close one -- so the emergency
liquidation could not liquidate. The kill switch stopped new positions opening
while leaving existing ones untouched, with no code path anywhere able to exit.

A test comment asserted this called kalshi_client.close_all_positions(). That
method did not exist.
"""

from unittest.mock import AsyncMock

import pytest
from core.safety import execute_ragnarok


@pytest.fixture
def kalshi(monkeypatch):
    import core.safety

    client = AsyncMock()
    client.request = AsyncMock(return_value={"orders": []})
    client.get_positions = AsyncMock(return_value=[])
    client.close_position = AsyncMock(return_value={"order_id": "close-1"})
    monkeypatch.setattr(core.safety, "kalshi_client", client)
    return client


class TestPositionsAreClosed:
    @pytest.mark.asyncio
    async def test_every_open_position_is_sold(self, kalshi):
        kalshi.get_positions = AsyncMock(
            return_value=[
                {"ticker": "KXA", "position": 10},
                {"ticker": "KXB", "position": 4},
            ]
        )

        result = await execute_ragnarok()

        assert result["positions_found"] == 2
        assert result["positions_closed"] == 2
        closed = sorted(c.args[0] for c in kalshi.close_position.await_args_list)
        assert closed == ["KXA", "KXB"]

    @pytest.mark.asyncio
    async def test_the_full_holding_is_sold_not_a_token_amount(self, kalshi):
        kalshi.get_positions = AsyncMock(return_value=[{"ticker": "KXA", "position": 37}])

        await execute_ragnarok()

        assert kalshi.close_position.await_args.args[1] == 37

    @pytest.mark.asyncio
    async def test_a_short_position_is_closed_by_magnitude(self, kalshi):
        """A negative holding is still exposure; -12 means close 12."""
        kalshi.get_positions = AsyncMock(return_value=[{"ticker": "KXA", "position": -12}])

        await execute_ragnarok()

        assert kalshi.close_position.await_args.args[1] == 12

    @pytest.mark.asyncio
    async def test_each_position_is_closed_on_its_own_side(self, kalshi):
        """A NO holding (negative quantity) must be sold as NO, a YES one as YES.

        close_one used to call close_position(ticker, count) with no side, so
        every close took the side="yes" default: a NO holding was answered
        with a "sell yes" order against a position that held no YES, instead
        of selling the NO actually held.
        """
        kalshi.get_positions = AsyncMock(
            return_value=[
                {"ticker": "KXNO", "position": -5},
                {"ticker": "KXYES", "position": 7},
            ]
        )

        await execute_ragnarok()

        sides = {c.args[0]: c.kwargs.get("side") for c in kalshi.close_position.await_args_list}
        assert sides == {"KXNO": "no", "KXYES": "yes"}

    @pytest.mark.asyncio
    async def test_flat_markets_are_left_alone(self, kalshi):
        kalshi.get_positions = AsyncMock(
            return_value=[{"ticker": "KXA", "position": 0}, {"ticker": "KXB", "position": 5}]
        )

        await execute_ragnarok()

        assert kalshi.close_position.await_count == 1


class TestOrdersAreCancelledFirst:
    @pytest.mark.asyncio
    async def test_resting_orders_are_cancelled_before_positions_close(self, kalshi):
        """Flattening while orders rest invites a fill against the exit."""
        sequence = []

        async def request(method, path, **_k):
            if method == "GET" and "orders" in path:
                return {"orders": [{"order_id": "o1"}]}
            if method == "DELETE":
                sequence.append("cancel")
                return {"ok": True}
            return None

        kalshi.request = AsyncMock(side_effect=request)
        kalshi.get_positions = AsyncMock(return_value=[{"ticker": "KXA", "position": 5}])
        kalshi.close_position = AsyncMock(
            side_effect=lambda *a, **k: sequence.append("close") or {"order_id": "c"}
        )

        await execute_ragnarok()

        assert sequence == ["cancel", "close"]


class TestTheEmergencyPathNeverRaises:
    @pytest.mark.asyncio
    async def test_unreadable_positions_still_report_cancelled_orders(self, kalshi):
        kalshi.get_positions = AsyncMock(side_effect=RuntimeError("API down"))

        result = await execute_ragnarok()

        assert result["status"] == "success"
        assert result["positions_closed"] == 0

    @pytest.mark.asyncio
    async def test_one_failed_close_does_not_abandon_the_others(self, kalshi):
        kalshi.get_positions = AsyncMock(
            return_value=[{"ticker": "KXA", "position": 5}, {"ticker": "KXB", "position": 5}]
        )

        async def flaky(ticker, count, side="yes"):
            if ticker == "KXA":
                raise RuntimeError("rejected")
            return {"order_id": "c"}

        kalshi.close_position = AsyncMock(side_effect=flaky)

        result = await execute_ragnarok()

        assert result["positions_found"] == 2
        assert result["positions_closed"] == 1


class TestTheClientCanExpressASell:
    @pytest.mark.asyncio
    async def test_close_position_sends_a_sell(self, monkeypatch):
        """place_order had no action field at all, so a sell was unexpressable.

        Arms live mode first: place_order now returns a simulated fill in paper
        mode without reaching the transport, so a test of what goes over the
        wire has to say it means the wire. That the guard intercepted this test
        is itself the point -- Ragnarok's flatten routes through close_position,
        so paper mode covers the emergency exit as well as ordinary entries.
        """
        from core import trading_mode
        from core.network import KalshiClient

        monkeypatch.setattr(trading_mode, "_live", True)

        client = KalshiClient.__new__(KalshiClient)
        sent = {}

        async def capture(method, path, json_data=None, **_k):
            sent.update(json_data or {})
            return {"order_id": "x"}

        client.request = capture
        await client.close_position("KXA", 10)

        assert sent["action"] == "sell"
        assert sent["count"] == 10
        assert sent["market_id"] == "KXA"
