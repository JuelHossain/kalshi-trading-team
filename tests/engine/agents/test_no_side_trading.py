"""The engine can now say a market is too expensive, not only too cheap.

side="yes" was hardcoded at the only order site, so the bot could express one
direction of disagreement with the market and discarded the other. A market it
judged overpriced -- half of all disagreements, and exactly as tradeable -- was
simply skipped.

On Kalshi the two sides sum to 1: holding NO at (1-k) pays 1 when the event
does not happen, so the NO edge is (1-p) - (1-k) = k - p, the mirror of the
YES edge.
"""

from unittest.mock import AsyncMock

import pytest
from agents.brain.simulation import best_side, kelly_fraction

from tests.engine.support import _debate, _opportunity


class TestSideSelection:
    @pytest.mark.parametrize(
        "probability,price,expected",
        [
            (0.90, 0.50, "yes"),  # far underpriced
            (0.55, 0.50, "yes"),  # slightly underpriced
            (0.45, 0.50, "no"),  # slightly overpriced
            (0.10, 0.50, "no"),  # far overpriced
            (0.30, 0.80, "no"),
            (0.80, 0.30, "yes"),
        ],
    )
    def test_the_cheaper_side_of_the_disagreement_is_chosen(self, probability, price, expected):
        assert best_side(probability, price)[0] == expected

    def test_the_no_edge_mirrors_the_yes_edge(self):
        """Overpriced by 10c is worth the same as underpriced by 10c."""
        _, _, _, under = best_side(0.60, 0.50)
        _, _, _, over = best_side(0.40, 0.50)
        assert under == pytest.approx(over)

    def test_a_fair_price_has_no_edge(self):
        assert best_side(0.50, 0.50)[3] == pytest.approx(0.0)

    def test_the_no_side_carries_mirrored_price_and_probability(self):
        side, side_price, side_probability, _ = best_side(0.30, 0.70)
        assert side == "no"
        assert side_price == pytest.approx(0.30)  # 1 - 0.70
        assert side_probability == pytest.approx(0.70)  # 1 - 0.30

    def test_kelly_works_unchanged_on_the_no_side(self):
        """Kelly takes the bought side's own numbers, so it needs no special case."""
        _, price, probability, _ = best_side(0.20, 0.60)
        assert kelly_fraction(probability, price) == pytest.approx((0.8 - 0.4) / (1 - 0.4))


class TestTheBrainApprovesNoTrades:
    @pytest.mark.asyncio
    async def test_an_overpriced_market_is_approved_as_no(self, cycle):
        """The case the old engine threw away."""
        cycle["brain"].run_debate = _debate(probability=0.20)

        await cycle["brain"].process_single_opportunity(_opportunity(kalshi_price=0.70))

        signal = await cycle["synapse"].executions.pop()
        assert signal is not None, "an overpriced market produced no trade"
        assert signal.side == "NO"
        assert signal.side_price == pytest.approx(0.30)
        assert signal.side_probability == pytest.approx(0.80)

    @pytest.mark.asyncio
    async def test_an_underpriced_market_is_still_yes(self, cycle):
        cycle["brain"].run_debate = _debate(probability=0.90)

        await cycle["brain"].process_single_opportunity(_opportunity(kalshi_price=0.50))

        signal = await cycle["synapse"].executions.pop()
        assert signal.side == "YES"


class TestTheHandPlacesNoOrders:
    @pytest.mark.asyncio
    async def test_the_order_is_sent_on_the_no_side(self, cycle):
        hand, kalshi = cycle["hand"], cycle["kalshi"]
        await cycle["vault"].initialize(100_000)
        # Tight book so the snipe check passes on either side.
        kalshi.get_orderbook = AsyncMock(
            return_value={
                "bids": [{"price": 68, "count": 800}],
                "asks": [{"price": 71, "count": 800}],
            }
        )

        cycle["brain"].run_debate = _debate(probability=0.20)
        await cycle["brain"].process_single_opportunity(_opportunity(kalshi_price=0.70))
        await hand.on_execution_ready(None)

        kalshi.place_order.assert_awaited_once()
        assert kalshi.place_order.await_args.kwargs["side"] == "no"

    @pytest.mark.asyncio
    async def test_the_no_entry_price_is_the_mirrored_book(self, cycle):
        """Buying NO crosses the YES bid, so the price is 100 - bid."""
        hand, kalshi = cycle["hand"], cycle["kalshi"]
        await cycle["vault"].initialize(100_000)
        kalshi.get_orderbook = AsyncMock(
            return_value={
                "bids": [{"price": 68, "count": 800}],
                "asks": [{"price": 71, "count": 800}],
            }
        )

        cycle["brain"].run_debate = _debate(probability=0.20)
        await cycle["brain"].process_single_opportunity(_opportunity(kalshi_price=0.70))
        await hand.on_execution_ready(None)

        # NO ask = 100 - YES bid = 32
        assert kalshi.place_order.await_args.kwargs["price"] == 32

    @pytest.mark.asyncio
    async def test_a_yes_trade_is_unaffected(self, cycle):
        """The mirroring must not disturb the side that already worked."""
        hand, kalshi = cycle["hand"], cycle["kalshi"]
        await cycle["vault"].initialize(100_000)

        cycle["brain"].run_debate = _debate(probability=0.90)
        await cycle["brain"].process_single_opportunity(_opportunity(kalshi_price=0.50))
        await hand.on_execution_ready(None)

        kalshi.place_order.assert_awaited_once()
        assert kalshi.place_order.await_args.kwargs["side"] == "yes"
