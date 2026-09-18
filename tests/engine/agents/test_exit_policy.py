"""When the engine leaves a position.

It gained the ability to close one, but nothing decided when to use it: every
holding rode to settlement unless a human ran Ragnarok. Holding binaries to
settlement is defensible -- they resolve to 0 or 100, so time favours a correct
forecast -- but a contract bought at 60c that has drifted to 5c is near-
certainly lost, and holding it converts "near-certainly" into "certainly".
"""

from unittest.mock import AsyncMock

import pytest
from agents.hand.exits import HOLD, average_entry_price_cents, evaluate_exit

# Fixtures shared with the trade-cycle tests.


def _book(yes_price_cents: int) -> dict:
    """A real Kalshi orderbook_fp quoting the market at `yes_price_cents`.

    _current_price_cents reads the resting bid on the position's own side --
    what closing it would actually fetch -- via parse_orderbook. These tests
    describe scenarios in terms of a single "the market is trading at X"
    price, so a self-consistent two-sided book (a YES bid at X and its
    mirror, a NO bid at 100 - X) reproduces exactly that for either side.
    Building this by hand rather than {"asks": [...]} because a literal
    "asks" key is not a shape any real Kalshi response has.
    """
    yes = max(1, min(99, yes_price_cents))
    no = 100 - yes
    return {
        "orderbook_fp": {
            "yes_dollars": [[f"{yes / 100:.2f}", "100"]],
            "no_dollars": [[f"{no / 100:.2f}", "100"]],
        }
    }


class TestStopLoss:
    def test_a_decisive_loss_is_cut(self):
        assert evaluate_exit(60, 20).should_exit

    def test_the_boundary_is_inclusive(self):
        """Entry 60c, 50% stop -> 30c exits."""
        assert evaluate_exit(60, 30).should_exit
        assert evaluate_exit(60, 31) == HOLD

    def test_the_reason_names_the_numbers(self):
        """The reason is recorded, so it has to be specific enough to audit."""
        reason = evaluate_exit(60, 20).reason
        assert "stop loss" in reason
        assert "60" in reason and "20" in reason

    def test_a_small_drawdown_is_held(self):
        assert evaluate_exit(60, 55) == HOLD


class TestTakeProfit:
    def test_most_of_the_upside_is_banked(self):
        """Entry 60c, 80% of the 40c move -> 92c exits."""
        assert evaluate_exit(60, 92).should_exit

    def test_just_short_of_the_target_is_held(self):
        assert evaluate_exit(60, 91) == HOLD

    def test_a_contract_already_at_the_top_cannot_divide_by_zero(self):
        """Entry at 99c leaves 1c of upside; entry at 100 would leave none."""
        assert evaluate_exit(99, 99) == HOLD


class TestExpiry:
    def test_a_losing_position_is_closed_before_settlement(self):
        assert evaluate_exit(60, 55, hours_to_expiry=1.0).should_exit

    def test_a_winning_position_is_left_to_settle(self):
        """Settlement pays 100; a thin pre-expiry book does not."""
        assert evaluate_exit(60, 70, hours_to_expiry=1.0) == HOLD

    def test_a_distant_expiry_does_not_trigger(self):
        assert evaluate_exit(60, 55, hours_to_expiry=48.0) == HOLD

    def test_unknown_expiry_is_not_treated_as_imminent(self):
        assert evaluate_exit(60, 55, hours_to_expiry=None) == HOLD


class TestBadInputHolds:
    """An exit computed from bad data is worse than no exit."""

    @pytest.mark.parametrize("entry,current", [(0, 50), (100, 50), (60, 0), (60, 150), (None, 50)])
    def test_impossible_prices_hold(self, entry, current):
        assert evaluate_exit(entry, current) == HOLD


class TestEntryPriceRecovery:
    def test_derived_from_exposure_and_quantity(self):
        assert average_entry_price_cents({"position": 10, "market_exposure": 600}) == 60

    def test_total_traded_is_accepted_as_a_fallback(self):
        assert average_entry_price_cents({"position": 4, "total_traded": 200}) == 50

    @pytest.mark.parametrize(
        "row",
        [
            {"position": 0, "market_exposure": 600},
            {"position": 10},
            {},
            {"position": 10, "market_exposure": 0},
        ],
    )
    def test_unrecoverable_rows_return_none(self, row):
        """None must propagate to a hold, not a guessed entry price."""
        assert average_entry_price_cents(row) is None


class TestTheHandActsOnIt:
    @pytest.mark.asyncio
    async def test_a_losing_position_is_closed(self, cycle):
        hand, kalshi = cycle["hand"], cycle["kalshi"]
        kalshi.get_positions = AsyncMock(
            return_value=[{"ticker": "KXA", "position": 10, "market_exposure": 600}]
        )
        kalshi.get_orderbook = AsyncMock(return_value=_book(20))

        closed = await hand.check_exits()

        assert closed == 1
        kalshi.close_position.assert_awaited_once_with("KXA", 10, side="yes")

    @pytest.mark.asyncio
    async def test_a_healthy_position_is_left_alone(self, cycle):
        hand, kalshi = cycle["hand"], cycle["kalshi"]
        kalshi.get_positions = AsyncMock(
            return_value=[{"ticker": "KXA", "position": 10, "market_exposure": 600}]
        )
        kalshi.get_orderbook = AsyncMock(return_value=_book(62))

        assert await hand.check_exits() == 0
        kalshi.close_position.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_an_unknown_entry_price_holds_rather_than_guesses(self, cycle):
        hand, kalshi = cycle["hand"], cycle["kalshi"]
        kalshi.get_positions = AsyncMock(return_value=[{"ticker": "KXA", "position": 10}])
        kalshi.get_orderbook = AsyncMock(return_value=_book(5))

        assert await hand.check_exits() == 0
        kalshi.close_position.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_a_failed_review_does_not_break_the_cycle(self, cycle):
        hand, kalshi = cycle["hand"], cycle["kalshi"]
        kalshi.get_positions = AsyncMock(side_effect=RuntimeError("API down"))

        assert await hand.check_exits() == 0

    @pytest.mark.asyncio
    async def test_one_failed_close_does_not_abandon_the_rest(self, cycle):
        hand, kalshi = cycle["hand"], cycle["kalshi"]
        kalshi.get_positions = AsyncMock(
            return_value=[
                {"ticker": "KXA", "position": 10, "market_exposure": 600},
                {"ticker": "KXB", "position": 10, "market_exposure": 600},
            ]
        )
        kalshi.get_orderbook = AsyncMock(return_value=_book(20))

        async def flaky(ticker, count, side="yes"):
            if ticker == "KXA":
                raise RuntimeError("rejected")
            return {"order_id": "c"}

        kalshi.close_position = AsyncMock(side_effect=flaky)

        assert await hand.check_exits() == 1


class TestNoPositionsAreValuedCorrectly:
    """A NO holding gains when the YES price falls.

    Valuing it as YES reads its stop-loss backwards: a NO position that is
    winning would look like it is losing and be closed at a profit it had not
    finished making -- or worse, a losing one would be held.
    """

    @pytest.mark.asyncio
    async def test_a_winning_no_position_is_not_closed(self, cycle):
        hand, kalshi = cycle["hand"], cycle["kalshi"]
        # Bought 10 NO at 40c (exposure 400, negative quantity = NO).
        kalshi.get_positions = AsyncMock(
            return_value=[{"ticker": "KXA", "position": -10, "market_exposure": 400}]
        )
        # YES has fallen to 10c, so NO is worth 90c. Entry was 40c, leaving 60c
        # of upside, so the 80% take-profit target is 88c -- 90c clears it.
        kalshi.get_orderbook = AsyncMock(return_value=_book(10))

        closed = await hand.check_exits()

        assert closed == 1, "a NO position at 90c against a 40c entry should take profit"
        assert kalshi.close_position.await_args.kwargs["side"] == "no"

    @pytest.mark.asyncio
    async def test_a_no_position_short_of_the_target_is_held(self, cycle):
        """Entry 40c, NO now 80c: a real gain, but under the 88c target."""
        hand, kalshi = cycle["hand"], cycle["kalshi"]
        kalshi.get_positions = AsyncMock(
            return_value=[{"ticker": "KXA", "position": -10, "market_exposure": 400}]
        )
        kalshi.get_orderbook = AsyncMock(return_value=_book(20))

        assert await hand.check_exits() == 0

    @pytest.mark.asyncio
    async def test_a_losing_no_position_is_stopped_out(self, cycle):
        hand, kalshi = cycle["hand"], cycle["kalshi"]
        # Bought 10 NO at 60c; YES has risen to 85c, so NO is worth 15c.
        kalshi.get_positions = AsyncMock(
            return_value=[{"ticker": "KXA", "position": -10, "market_exposure": 600}]
        )
        kalshi.get_orderbook = AsyncMock(return_value=_book(85))

        assert await hand.check_exits() == 1
        assert kalshi.close_position.await_args.kwargs["side"] == "no"

    @pytest.mark.asyncio
    async def test_a_healthy_no_position_is_held(self, cycle):
        hand, kalshi = cycle["hand"], cycle["kalshi"]
        # Bought 10 NO at 60c; YES at 45c means NO is worth 55c -- a small loss.
        kalshi.get_positions = AsyncMock(
            return_value=[{"ticker": "KXA", "position": -10, "market_exposure": 600}]
        )
        kalshi.get_orderbook = AsyncMock(return_value=_book(45))

        assert await hand.check_exits() == 0
        kalshi.close_position.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_yes_positions_are_still_valued_as_before(self, cycle):
        """The mirroring must not disturb the side that already worked."""
        hand, kalshi = cycle["hand"], cycle["kalshi"]
        kalshi.get_positions = AsyncMock(
            return_value=[{"ticker": "KXA", "position": 10, "market_exposure": 600}]
        )
        kalshi.get_orderbook = AsyncMock(return_value=_book(62))

        assert await hand.check_exits() == 0
