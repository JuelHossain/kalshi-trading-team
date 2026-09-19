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
from core import ledger
from core.safety import execute_ragnarok


def _orderbook(yes_bid_cents: int) -> dict:
    """A real orderbook_fp quoting YES at `yes_bid_cents`, NO at its mirror."""
    yes = max(1, min(99, yes_bid_cents))
    no = 100 - yes
    return {
        "orderbook_fp": {
            "yes_dollars": [[f"{yes / 100:.2f}", "100"]],
            "no_dollars": [[f"{no / 100:.2f}", "100"]],
        }
    }


@pytest.fixture
def kalshi(monkeypatch):
    import core.safety

    # These cover the live flatten; paper-pinned Ragnarok leaves Kalshi alone
    # (see TestPaperRagnarok below).
    monkeypatch.setenv("IS_PAPER_TRADING", "false")

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

        # Still reports the cancels, but "cannot read" is not "nothing to
        # close": it must not claim to be complete.
        assert result["status"] == "partial"
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

        # Kalshi V2: selling YES is an "ask", capped at the position held.
        assert sent["side"] == "ask"
        assert sent["reduce_only"] is True
        assert sent["count"] == "10.00"
        assert sent["ticker"] == "KXA"


class TestRagnarokRecordsTheExitInTheLedger:
    """A Ragnarok close is the same kind of early exit as check_exits'own:
    without recording it, the fill sits unsettled until the market resolves
    and then gets priced off however it settled, not off what the emergency
    flatten actually fetched (see core.ledger.record_exit)."""

    @pytest.mark.asyncio
    async def test_a_live_close_is_recorded_at_the_book_s_bid(self, kalshi):
        ledger.record_decision("KXA", 0.60, outcome="APPROVED", estimated_probability=0.3)
        ledger.record_fill("KXA", 600, "kalshi-order-kxa", side="yes", price_cents=60, count=10)
        kalshi.get_positions = AsyncMock(
            return_value=[{"ticker": "KXA", "position": 10, "market_exposure": 600}]
        )
        kalshi.get_orderbook = AsyncMock(return_value=_orderbook(20))

        await execute_ragnarok()

        (fill,) = ledger.recent_fills()
        assert fill["exit_price_cents"] == 20
        assert fill["closed"] is True
        assert fill["pnl_cents"] == -400  # (20 - 60)c x 10, not a settlement guess

    @pytest.mark.asyncio
    async def test_an_unreadable_book_still_marks_the_row_closed(self, kalshi):
        """The flatten already happened; a failed price read must not leave
        the row looking untouched and open to being priced off settlement."""
        ledger.record_decision("KXB", 0.60, outcome="APPROVED", estimated_probability=0.3)
        ledger.record_fill("KXB", 600, "kalshi-order-kxb", side="yes", price_cents=60, count=10)
        kalshi.get_positions = AsyncMock(
            return_value=[{"ticker": "KXB", "position": 10, "market_exposure": 600}]
        )
        kalshi.get_orderbook = AsyncMock(side_effect=RuntimeError("book unreadable"))

        await execute_ragnarok()

        (fill,) = ledger.recent_fills()
        assert fill["exit_price_cents"] is None
        assert fill["closed"] is True
        assert fill["pnl_cents"] is None

    @pytest.mark.asyncio
    async def test_an_unreadable_book_stays_unpriced_even_after_the_market_settles(self, kalshi):
        """The exit above leaves exit_price_cents NULL with exited_at set.
        Once the market later settles, that row must not fall back to the
        settlement formula -- it is no longer the position settlement
        priced -- so pnl_cents stays None and realised_edge leaves it out.
        """
        ledger.record_decision("KXC", 0.60, outcome="APPROVED", estimated_probability=0.3)
        ledger.record_fill("KXC", 600, "kalshi-order-kxc", side="yes", price_cents=60, count=10)
        kalshi.get_positions = AsyncMock(
            return_value=[{"ticker": "KXC", "position": 10, "market_exposure": 600}]
        )
        kalshi.get_orderbook = AsyncMock(side_effect=RuntimeError("book unreadable"))

        await execute_ragnarok()
        ledger.record_settlement("KXC", settled_yes=True)

        (fill,) = ledger.recent_fills()
        assert fill["settled_yes"] == 1
        assert fill["pnl_cents"] is None

        edge = ledger.realised_edge()
        assert edge["n"] == 0


class TestPaperRagnarok:
    """Pinned to paper, Ragnarok flattens the paper book and never touches
    Kalshi -- it used to cancel real orders while paper-filling the closes,
    leaving real positions open behind a "closed N/N" report."""

    @pytest.mark.asyncio
    async def test_the_paper_book_is_flattened_and_kalshi_is_not_written(self, monkeypatch):
        import core.safety
        from core import trading_mode

        monkeypatch.setenv("IS_PAPER_TRADING", "true")
        trading_mode.reset_paper_positions()
        trading_mode.paper_fill("KXP", "no", 40, 5, "buy")
        client = AsyncMock()
        client.get_positions = AsyncMock(return_value=[{"ticker": "KXREAL", "position": 3}])
        client.close_position = AsyncMock(return_value={"order_id": "p"})
        monkeypatch.setattr(core.safety, "kalshi_client", client)

        result = await execute_ragnarok()

        client.request.assert_not_awaited()  # no real cancels
        client.close_position.assert_awaited_once_with("KXP", 5, side="no")
        assert result["mode"] == "paper"
        assert result["real_positions_untouched"] == 1
        trading_mode.reset_paper_positions()
