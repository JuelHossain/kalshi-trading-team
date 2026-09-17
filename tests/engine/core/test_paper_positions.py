"""Paper mode must know what it holds, or it stacks into the same market.

The first successful paper run filled NYGLAR-NYG twice and SEAARI-ARI twice.
has_open_position read Kalshi's portfolio, where a simulated fill never
appears, got an empty book, and answered "not held". The guard against
concentrating exposure was blind in exactly the mode meant to prove it.
"""

import pytest
from agents.hand.execution import has_open_position
from agents.hand.exits import average_entry_price_cents
from core import trading_mode


@pytest.fixture(autouse=True)
def clean_paper_book():
    trading_mode.reset_paper_positions()
    trading_mode.set_live(False)
    yield
    trading_mode.reset_paper_positions()


class _Client:
    def __init__(self, positions=None, raise_=False):
        self._positions = positions or []
        self._raise = raise_
        self.calls = 0

    async def get_positions(self):
        self.calls += 1
        if self._raise:
            raise RuntimeError("portfolio unavailable")
        return self._positions


class TestPaperFillsAreRemembered:
    def test_a_yes_buy_is_a_positive_holding(self):
        trading_mode.paper_fill("T", "yes", 35, 7, "buy")
        assert trading_mode.paper_position("T") == 7

    def test_a_no_buy_is_a_negative_holding(self):
        trading_mode.paper_fill("T", "no", 74, 4, "buy")
        assert trading_mode.paper_position("T") == -4

    def test_buying_twice_accumulates(self):
        """This is what happened live; the book must at least record it."""
        trading_mode.paper_fill("T", "yes", 35, 3, "buy")
        trading_mode.paper_fill("T", "yes", 35, 7, "buy")
        assert trading_mode.paper_position("T") == 10

    def test_selling_everything_closes_the_position(self):
        trading_mode.paper_fill("T", "yes", 35, 7, "buy")
        trading_mode.paper_fill("T", "yes", 1, 7, "sell")
        assert trading_mode.paper_position("T") == 0
        assert trading_mode.paper_positions() == []

    def test_selling_a_no_holding_closes_it(self):
        trading_mode.paper_fill("T", "no", 74, 4, "buy")
        trading_mode.paper_fill("T", "no", 99, 4, "sell")
        assert trading_mode.paper_position("T") == 0

    def test_a_partial_sell_reduces_the_holding(self):
        trading_mode.paper_fill("T", "yes", 35, 10, "buy")
        trading_mode.paper_fill("T", "yes", 1, 4, "sell")
        assert trading_mode.paper_position("T") == 6

    def test_unheld_ticker_is_zero(self):
        assert trading_mode.paper_position("NOPE") == 0

    def test_reset_forgets_everything(self):
        trading_mode.paper_fill("T", "yes", 35, 7, "buy")
        trading_mode.reset_paper_positions()
        assert trading_mode.paper_positions() == []


class TestPaperRowsSatisfyTheExitReview:
    def test_entry_price_is_derivable_from_a_paper_row(self):
        """The exit policy derives entry from exposure / quantity."""
        trading_mode.paper_fill("T", "yes", 35, 7, "buy")
        row = trading_mode.paper_positions()[0]
        assert average_entry_price_cents(row) == 35

    def test_a_partial_sell_keeps_the_entry_price_honest(self):
        trading_mode.paper_fill("T", "yes", 40, 10, "buy")
        trading_mode.paper_fill("T", "yes", 1, 5, "sell")
        row = trading_mode.paper_positions()[0]
        assert average_entry_price_cents(row) == 40

    def test_rows_are_copies_not_the_live_book(self):
        trading_mode.paper_fill("T", "yes", 35, 7, "buy")
        row = trading_mode.paper_positions()[0]
        row["position"] = 999
        assert trading_mode.paper_position("T") == 7


class TestTheStackGuardSeesPaperHoldings:
    @pytest.mark.asyncio
    async def test_the_regression_a_paper_holding_blocks_a_second_entry(self):
        trading_mode.paper_fill("T", "yes", 35, 7, "buy")
        client = _Client(positions=[])

        assert await has_open_position(client, "T") is True

    @pytest.mark.asyncio
    async def test_paper_holding_is_checked_before_kalshi_is_asked(self):
        trading_mode.paper_fill("T", "yes", 35, 7, "buy")
        client = _Client(positions=[])

        await has_open_position(client, "T")

        assert client.calls == 0

    @pytest.mark.asyncio
    async def test_a_different_ticker_is_not_blocked(self):
        trading_mode.paper_fill("T", "yes", 35, 7, "buy")
        assert await has_open_position(_Client(positions=[]), "OTHER") is False

    @pytest.mark.asyncio
    async def test_kalshi_holdings_are_still_respected(self):
        client = _Client(positions=[{"ticker": "K", "position": 3}])
        assert await has_open_position(client, "K") is True

    @pytest.mark.asyncio
    async def test_an_unreadable_portfolio_still_fails_closed(self):
        assert await has_open_position(_Client(raise_=True), "T") is True

    @pytest.mark.asyncio
    async def test_no_client_and_no_paper_holding_is_not_held(self):
        assert await has_open_position(None, "T") is False
