"""The Hand must read the orderbook Kalshi actually sends.

Observed live: every approved signal died at "Snipe check failed: Spread
too wide: 10c". Senses had already filtered those same markets to an 8c
spread or better from the same data. 10c is exactly 55 - 45, the two
defaults the old lookup fell back to when its keys were missing -- which
they always were, because Kalshi has never returned {"bids": [...]}.

The existing tests constructed that invented shape, so the suite stayed
green while the engine could not place a single order.

The book below is a real one, captured through the engine's own client.
"""

import pytest
from agents.hand.execution import parse_orderbook, snipe_check

# KXNFLGAME-26SEP20SEAARI-ARI, as returned by GET /markets/{t}/orderbook.
# Levels ascend by price: the first YES entry is a 1c junk bid, not the best.
REAL_BOOK = {
    "orderbook_fp": {
        "yes_dollars": [
            ["0.0100", "3320.00"],
            ["0.3000", "5.00"],
            ["0.3200", "21426.03"],
            ["0.3300", "21717.15"],
        ],
        "no_dollars": [
            ["0.6200", "5.00"],
            ["0.6300", "72138.00"],
            ["0.6400", "74536.56"],
            ["0.6500", "77618.97"],
        ],
    }
}

LEGACY_BOOK = {"orderbook": {"yes": [[1, 3320], [33, 21717]], "no": [[65, 77618]]}}

FIXTURE_BOOK = {
    "bids": [{"price": 45, "count": 1000}],
    "asks": [{"price": 48, "count": 1000}],
}


class _Client:
    def __init__(self, book):
        self.book = book

    async def get_orderbook(self, ticker):
        return self.book


async def _log(message, level="INFO"):
    pass


class TestRealBookShape:
    def test_best_yes_bid_is_the_highest_level_not_the_first(self):
        """The 1c junk bid at the front must not be mistaken for the best."""
        book = parse_orderbook(REAL_BOOK, side="yes")
        assert book["best_bid"] == 33

    def test_yes_ask_is_the_mirror_of_the_best_no_bid(self):
        """Kalshi has no asks: a NO bid at 65 is a YES ask at 35."""
        book = parse_orderbook(REAL_BOOK, side="yes")
        assert book["best_ask"] == 35

    def test_the_real_spread_is_two_cents_not_ten(self):
        book = parse_orderbook(REAL_BOOK, side="yes")
        assert book["best_ask"] - book["best_bid"] == 2

    def test_ask_levels_carry_the_resting_contracts(self):
        book = parse_orderbook(REAL_BOOK, side="yes")
        price, count = book["ask_levels"][0]
        assert price == 35
        assert count == pytest.approx(77618.97)

    def test_ask_levels_ascend_from_the_best_price(self):
        prices = [p for p, _ in parse_orderbook(REAL_BOOK, side="yes")["ask_levels"]]
        assert prices == sorted(prices)
        assert prices[0] == 35

    def test_no_side_is_the_mirror(self):
        book = parse_orderbook(REAL_BOOK, side="no")
        assert book["best_bid"] == 65
        assert book["best_ask"] == 67  # 100 - best YES bid of 33
        assert book["best_ask"] - book["best_bid"] == 2


class TestSnipeCheckOnTheRealBook:
    @pytest.mark.asyncio
    async def test_the_regression_a_real_book_passes(self):
        """This exact book was rejected at 10c spread six times in a row."""
        result = await snipe_check(_Client(REAL_BOOK), "T", _log, side="yes")

        assert result["valid"] is True, result
        assert result["spread"] == 2
        assert result["entry_price"] == 35

    @pytest.mark.asyncio
    async def test_depth_is_measured_where_the_order_would_fill(self):
        """77,618 contracts rest at 35c; a $75 stake is not a depth problem."""
        result = await snipe_check(_Client(REAL_BOOK), "T", _log, max_stake_cents=7500, side="yes")
        assert result["valid"] is True

    @pytest.mark.asyncio
    async def test_thin_depth_at_the_best_ask_is_still_refused(self):
        thin = {
            "orderbook_fp": {
                "yes_dollars": [["0.3300", "5.00"]],
                "no_dollars": [["0.6500", "3.00"]],  # 3 contracts at 35c
            }
        }
        result = await snipe_check(_Client(thin), "T", _log, max_stake_cents=7500)
        assert result["valid"] is False
        assert "depth" in result["reason"]

    @pytest.mark.asyncio
    async def test_a_genuinely_wide_book_is_still_rejected(self):
        wide = {
            "orderbook_fp": {
                "yes_dollars": [["0.3000", "100.00"]],
                "no_dollars": [["0.6000", "100.00"]],  # ask 40, bid 30
            }
        }
        result = await snipe_check(_Client(wide), "T", _log)
        assert result["valid"] is False
        assert result["reason"] == "Spread too wide: 10¢"

    @pytest.mark.asyncio
    async def test_no_side_snipe_uses_no_prices(self):
        result = await snipe_check(_Client(REAL_BOOK), "T", _log, side="no")
        assert result["valid"] is True
        assert result["entry_price"] == 67


class TestOtherShapesStillWork:
    def test_previous_api_shape_in_integer_cents(self):
        book = parse_orderbook(LEGACY_BOOK, side="yes")
        assert (book["best_bid"], book["best_ask"]) == (33, 35)

    def test_the_test_fixture_shape_is_read_as_explicit_asks(self):
        """Existing tests build this; their spread and depth cases stay valid."""
        book = parse_orderbook(FIXTURE_BOOK, side="yes")
        assert (book["best_bid"], book["best_ask"]) == (45, 48)
        assert book["ask_levels"] == [(48, 1000.0)]

    def test_fixture_shape_mirrors_for_the_no_side(self):
        book = parse_orderbook(FIXTURE_BOOK, side="no")
        assert (book["best_bid"], book["best_ask"]) == (52, 55)


class TestUnreadableBooksFailLoudlyNotSilently:
    def test_unknown_keys_are_not_a_ten_cent_spread(self):
        """The regression in one line: no keys must never mean 45/55."""
        assert parse_orderbook({"something_else": 1}) is None

    def test_none_is_unreadable(self):
        assert parse_orderbook(None) is None

    @pytest.mark.asyncio
    async def test_snipe_reports_unreadable_rather_than_a_fake_spread(self):
        result = await snipe_check(_Client({"unexpected": True}), "T", _log)
        assert result["valid"] is False
        assert result["reason"] == "orderbook unreadable"
        assert "10" not in result["reason"]

    @pytest.mark.asyncio
    async def test_an_empty_side_is_reported_as_empty(self):
        empty = {"orderbook_fp": {"yes_dollars": [["0.3300", "5"]], "no_dollars": []}}
        result = await snipe_check(_Client(empty), "T", _log)
        assert result["valid"] is False
        assert "empty" in result["reason"]

    def test_malformed_levels_are_skipped_not_fatal(self):
        messy = {
            "orderbook_fp": {
                "yes_dollars": [["oops", "1"], ["0.3300", "5"], [None]],
                "no_dollars": [["0.6500", "x"], ["0.6400", "9"]],
            }
        }
        book = parse_orderbook(messy, side="yes")
        assert book["best_bid"] == 33
        assert book["best_ask"] == 36
