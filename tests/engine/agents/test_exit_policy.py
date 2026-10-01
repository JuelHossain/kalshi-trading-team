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
    """These positions come from kalshi.get_positions(): real Kalshi
    exposure. check_exits only reviews that book in live mode (see
    check_exits) -- a paper cycle cannot actually flatten a real position,
    only simulate doing so, which would misreport it as closed and corrupt
    the paper book with a phantom fill for a ticker it never bought. Live
    mode is what makes closing a real position meaningful, so that is what
    these exercise; TestAPaperExitCreditsTheBankroll covers the paper path.
    """

    @pytest.mark.asyncio
    async def test_a_losing_position_is_closed(self, cycle):
        from core import trading_mode

        hand, kalshi = cycle["hand"], cycle["kalshi"]
        trading_mode.set_live(True)
        kalshi.get_positions = AsyncMock(
            return_value=[{"ticker": "KXA", "position": 10, "market_exposure": 600}]
        )
        kalshi.get_orderbook = AsyncMock(return_value=_book(20))

        closed = await hand.check_exits()

        assert closed == 1
        kalshi.close_position.assert_awaited_once_with("KXA", 10, side="yes")

    @pytest.mark.asyncio
    async def test_a_healthy_position_is_left_alone(self, cycle):
        from core import trading_mode

        hand, kalshi = cycle["hand"], cycle["kalshi"]
        trading_mode.set_live(True)
        kalshi.get_positions = AsyncMock(
            return_value=[{"ticker": "KXA", "position": 10, "market_exposure": 600}]
        )
        kalshi.get_orderbook = AsyncMock(return_value=_book(62))

        assert await hand.check_exits() == 0
        kalshi.close_position.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_an_unknown_entry_price_holds_rather_than_guesses(self, cycle):
        from core import trading_mode

        hand, kalshi = cycle["hand"], cycle["kalshi"]
        trading_mode.set_live(True)
        kalshi.get_positions = AsyncMock(return_value=[{"ticker": "KXA", "position": 10}])
        kalshi.get_orderbook = AsyncMock(return_value=_book(5))

        assert await hand.check_exits() == 0
        kalshi.close_position.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_a_failed_review_does_not_break_the_cycle(self, cycle):
        from core import trading_mode

        hand, kalshi = cycle["hand"], cycle["kalshi"]
        trading_mode.set_live(True)
        kalshi.get_positions = AsyncMock(side_effect=RuntimeError("API down"))

        assert await hand.check_exits() == 0

    @pytest.mark.asyncio
    async def test_one_failed_close_does_not_abandon_the_rest(self, cycle):
        from core import trading_mode

        hand, kalshi = cycle["hand"], cycle["kalshi"]
        trading_mode.set_live(True)
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

    Live mode, for the same reason as TestTheHandActsOnIt: these positions
    are real Kalshi exposure (from get_positions()), and check_exits only
    acts on that book when it can actually flatten it.
    """

    @pytest.mark.asyncio
    async def test_a_winning_no_position_is_not_closed(self, cycle):
        from core import trading_mode

        hand, kalshi = cycle["hand"], cycle["kalshi"]
        trading_mode.set_live(True)
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
        from core import trading_mode

        hand, kalshi = cycle["hand"], cycle["kalshi"]
        trading_mode.set_live(True)
        kalshi.get_positions = AsyncMock(
            return_value=[{"ticker": "KXA", "position": -10, "market_exposure": 400}]
        )
        kalshi.get_orderbook = AsyncMock(return_value=_book(20))

        assert await hand.check_exits() == 0

    @pytest.mark.asyncio
    async def test_a_losing_no_position_is_stopped_out(self, cycle):
        from core import trading_mode

        hand, kalshi = cycle["hand"], cycle["kalshi"]
        trading_mode.set_live(True)
        # Bought 10 NO at 60c; YES has risen to 85c, so NO is worth 15c.
        kalshi.get_positions = AsyncMock(
            return_value=[{"ticker": "KXA", "position": -10, "market_exposure": 600}]
        )
        kalshi.get_orderbook = AsyncMock(return_value=_book(85))

        assert await hand.check_exits() == 1
        assert kalshi.close_position.await_args.kwargs["side"] == "no"

    @pytest.mark.asyncio
    async def test_a_healthy_no_position_is_held(self, cycle):
        from core import trading_mode

        hand, kalshi = cycle["hand"], cycle["kalshi"]
        trading_mode.set_live(True)
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
        from core import trading_mode

        hand, kalshi = cycle["hand"], cycle["kalshi"]
        trading_mode.set_live(True)
        kalshi.get_positions = AsyncMock(
            return_value=[{"ticker": "KXA", "position": 10, "market_exposure": 600}]
        )
        kalshi.get_orderbook = AsyncMock(return_value=_book(62))

        assert await hand.check_exits() == 0


class TestLiveModeIgnoresThePaperBook:
    """check_exits merged trading_mode.paper_positions() unconditionally.

    On a live cycle that is a real hazard, not just a mislabel: a ticker held
    only on paper -- left over from an earlier paper soak and reloaded by
    load_paper_positions at boot -- would be reviewed as though it were real
    Kalshi exposure, and a paper-only exit called close_position, which
    places a real reduce-only sell order on Kalshi for contracts the live
    account may not hold at all. It would keep firing every cycle until the
    market settled, and if the live account happened to hold the same side
    (bought separately), it would sell real contracts out from under it.
    """

    @pytest.fixture(autouse=True)
    def clean_paper_book(self):
        from core import trading_mode

        trading_mode.reset_paper_positions()
        yield
        trading_mode.reset_paper_positions()

    @pytest.mark.asyncio
    async def test_a_paper_only_holding_is_not_closed_on_a_live_cycle(self, cycle):
        from core import trading_mode

        hand, kalshi = cycle["hand"], cycle["kalshi"]
        trading_mode.paper_fill("KXPAPER", "yes", 35, 10, "buy")
        trading_mode.set_live(True)
        kalshi.get_positions = AsyncMock(return_value=[])
        # Would stop out at 15c against a 35c paper entry, if it were reviewed.
        kalshi.get_orderbook = AsyncMock(return_value=_book(15))

        closed = await hand.check_exits()

        assert closed == 0
        kalshi.close_position.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_the_same_holding_is_still_reviewed_on_a_paper_cycle(self, cycle):
        """The gate must only refuse live cycles, not break the feature it
        was built for."""
        from core import trading_mode

        hand, kalshi = cycle["hand"], cycle["kalshi"]
        trading_mode.paper_fill("KXPAPER", "yes", 35, 10, "buy")
        trading_mode.set_live(False)
        kalshi.get_positions = AsyncMock(return_value=[])
        kalshi.get_orderbook = AsyncMock(return_value=_book(15))

        closed = await hand.check_exits()

        assert closed == 1
        kalshi.close_position.assert_awaited_once_with("KXPAPER", 10, side="yes")


class TestAPaperExitCreditsTheBankroll:
    """close_position asks Kalshi for a 1c marketable limit so a real
    emergency exit is not left resting in the book -- see
    KalshiClient.close_position. In paper mode that 1c never reaches
    trading_mode.paper_fill's cash accounting (crediting it would credit a
    cent a contract); check_exits is what has to credit the real proceeds,
    because it is the one place that already reads the current bid to decide
    whether to exit at all.
    """

    @pytest.fixture(autouse=True)
    def clean_paper_book(self):
        from core import trading_mode

        trading_mode.reset_paper_positions()
        yield
        trading_mode.reset_paper_positions()

    @pytest.mark.asyncio
    async def test_a_stopped_out_yes_position_credits_the_current_bid(self, cycle):
        from core import trading_mode

        hand, kalshi = cycle["hand"], cycle["kalshi"]
        trading_mode.seed_paper_cash(100_000)
        trading_mode.paper_fill("KXPAPER", "yes", 35, 10, "buy")
        assert trading_mode.paper_cash() == 100_000 - 350

        trading_mode.set_live(False)
        kalshi.get_positions = AsyncMock(return_value=[])
        kalshi.get_orderbook = AsyncMock(return_value=_book(15))  # stops out

        closed = await hand.check_exits()

        assert closed == 1
        # Credited at the 15c bid the decision was made against, not the 1c
        # marketable-limit tick close_position asks Kalshi for.
        assert trading_mode.paper_cash() == 100_000 - 350 + 15 * 10

    @pytest.mark.asyncio
    async def test_a_live_exit_does_not_touch_the_paper_bankroll(self, cycle):
        """The credit is paper-only: a live close is real money, tracked by
        the vault through execute_order/vault.confirm_reservation, not by
        the paper bankroll."""
        from core import trading_mode

        hand, kalshi = cycle["hand"], cycle["kalshi"]
        trading_mode.seed_paper_cash(100_000)
        trading_mode.set_live(True)
        kalshi.get_positions = AsyncMock(
            return_value=[{"ticker": "KXA", "position": 10, "market_exposure": 600}]
        )
        kalshi.get_orderbook = AsyncMock(return_value=_book(20))  # stops out

        closed = await hand.check_exits()

        assert closed == 1
        assert trading_mode.paper_cash() == 100_000


class TestPaperModeNeverActsOnARealPosition:
    """A paper cycle's review list used to be trading_mode.paper_positions()
    *plus* the real account's kalshi.get_positions(). When a real holding
    tripped the exit policy, close_position went to paper_fill (not live),
    which:
      (1) never actually sold the real position on Kalshi -- it stayed open
          -- while check_exits still counted it closed and credited the
          paper bankroll for the "sale", repeatably, every cycle the policy
          kept tripping on it; and
      (2) wrote a phantom short into the persisted paper book for a ticker
          the paper book never bought (a sell with nothing on the other
          side), which, once persisted, survives a restart the same as a
          real paper holding does.

    Exercises the real KalshiClient.close_position -> place_order ->
    paper_fill chain (only get_positions/get_orderbook are stubbed), the
    same path production goes through, not a bare AsyncMock standing in for
    close_position.
    """

    @pytest.fixture(autouse=True)
    def clean_paper_book(self):
        from core import trading_mode

        trading_mode.reset_paper_positions()
        yield
        trading_mode.reset_paper_positions()

    @pytest.mark.asyncio
    async def test_a_real_holding_is_never_closed_or_credited_on_paper_cycles(self, cycle):
        from core import trading_mode
        from core.network import KalshiClient

        hand = cycle["hand"]
        trading_mode.set_live(False)
        trading_mode.seed_paper_cash(100_000)

        # __new__ skips KalshiClient.__init__ (credentials, an HTTP
        # session): close_position/place_order never touch either of those
        # while paper mode is engaged, so none of it is needed here.
        real_client = KalshiClient.__new__(KalshiClient)
        real_client.get_positions = AsyncMock(
            return_value=[{"ticker": "KXREAL", "position": 10, "market_exposure": 600}]
        )
        real_client.get_orderbook = AsyncMock(return_value=_book(20))  # stops out
        hand.kalshi_client = real_client

        for _ in range(5):
            closed = await hand.check_exits()
            assert closed == 0, "a real position must not be closed on a paper cycle"

        assert trading_mode.paper_cash() == 100_000, "no phantom credit for a real position"
        assert trading_mode.paper_positions() == [], "no phantom short recorded"
