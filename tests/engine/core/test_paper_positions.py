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


class TestThePaperBookSurvivesARestart:
    """The book lived only in the module dict.

    Every restart source -- systemd's Restart=always, deploy/update.sh, a
    crash, POST /engine/restart's os.execv -- emptied it: has_open_position
    then answered "not held" for a market the soak already bought, and
    check_exits could not see the earlier holding. (The kill switch and
    /cancel used to restart the process too; b70be88 stopped that, but the
    other restart sources remain.) load_paper_positions is what a fresh
    process calls at boot to recover it.
    """

    def test_the_regression_a_restart_recovers_the_book(self):
        trading_mode.paper_fill("T", "yes", 35, 7, "buy")
        trading_mode.paper_fill("U", "no", 60, 3, "buy")

        # A restart is a fresh process: nothing survives but disk. Clearing
        # the dict directly (not reset_paper_positions, which also wipes the
        # disk copy) simulates that without a second process.
        trading_mode._paper_positions.clear()
        assert trading_mode.paper_positions() == []

        trading_mode.load_paper_positions()

        assert trading_mode.paper_position("T") == 7
        assert trading_mode.paper_position("U") == -3

    def test_a_sell_persists_too(self):
        trading_mode.paper_fill("T", "yes", 35, 10, "buy")
        trading_mode.paper_fill("T", "yes", 1, 4, "sell")

        trading_mode._paper_positions.clear()
        trading_mode.load_paper_positions()

        assert trading_mode.paper_position("T") == 6

    def test_reset_clears_the_disk_copy_too(self):
        """Otherwise the next boot's load would resurrect what reset erased."""
        trading_mode.paper_fill("T", "yes", 35, 7, "buy")
        trading_mode.reset_paper_positions()

        trading_mode.load_paper_positions()

        assert trading_mode.paper_positions() == []


class TestSettlingAPaperPosition:
    def test_the_winning_side_is_paid_a_dollar_a_contract(self):
        trading_mode.paper_fill("T", "yes", 35, 7, "buy")

        payout = trading_mode.settle_paper_position("T", won_yes=True)

        assert payout == 700  # 7 contracts x $1
        assert trading_mode.paper_position("T") == 0

    def test_a_no_holding_wins_when_the_market_settles_no(self):
        trading_mode.paper_fill("T", "no", 74, 4, "buy")

        payout = trading_mode.settle_paper_position("T", won_yes=False)

        assert payout == 400

    def test_the_losing_side_is_paid_nothing(self):
        trading_mode.paper_fill("T", "yes", 35, 7, "buy")

        payout = trading_mode.settle_paper_position("T", won_yes=False)

        assert payout == 0
        assert trading_mode.paper_position("T") == 0

    def test_an_unheld_ticker_pays_nothing(self):
        assert trading_mode.settle_paper_position("NOPE", won_yes=True) == 0

    def test_settling_removes_it_from_the_book_on_disk_too(self):
        trading_mode.paper_fill("T", "yes", 35, 7, "buy")
        trading_mode.settle_paper_position("T", won_yes=True)

        trading_mode._paper_positions["T"] = {
            "ticker": "T",
            "position": 999,
            "market_exposure": 1,
        }  # tamper with memory only
        trading_mode.load_paper_positions()

        assert trading_mode.paper_position("T") == 0


class TestThePaperBankroll:
    """authorize_cycle overwrote vault.current_balance with the real Kalshi
    balance every cycle, so paper spending never depleted it, Kelly always
    sized on the full real balance, and the hard floor and kill switch --
    both keyed off vault.current_balance -- could not trip on a paper loss.

    The bankroll tracked here is what authorize_cycle now feeds the vault on
    a paper cycle instead of the real balance.
    """

    def test_seeding_sets_the_starting_balance(self):
        trading_mode.seed_paper_cash(100_000)
        assert trading_mode.paper_cash() == 100_000

    def test_seeding_again_does_not_reset_it(self):
        """A restart must resume the paper P&L already accrued, not
        overwrite it with the real balance again -- the exact bug this
        exists to fix."""
        trading_mode.seed_paper_cash(100_000)
        trading_mode.adjust_paper_cash(-30_000)

        trading_mode.seed_paper_cash(999_999)  # a later boot's real balance

        assert trading_mode.paper_cash() == 70_000

    def test_adjust_before_seeding_is_a_noop(self):
        assert trading_mode.paper_cash() is None
        trading_mode.adjust_paper_cash(-500)
        assert trading_mode.paper_cash() is None

    def test_a_buy_debits_the_bankroll(self):
        trading_mode.seed_paper_cash(100_000)
        trading_mode.paper_fill("T", "yes", 35, 7, "buy")
        assert trading_mode.paper_cash() == 100_000 - 35 * 7

    def test_two_buys_debit_cumulatively(self):
        trading_mode.seed_paper_cash(100_000)
        trading_mode.paper_fill("T", "yes", 35, 7, "buy")
        trading_mode.paper_fill("U", "no", 60, 3, "buy")
        assert trading_mode.paper_cash() == 100_000 - 35 * 7 - 60 * 3

    def test_a_sell_through_paper_fill_alone_does_not_move_the_bankroll(self):
        """A sell's `price` is close_position's 1c marketable-limit tick, not
        what the position was worth -- crediting it here would credit a cent
        a contract. The real credit is the caller's job (check_exits), which
        knows the current bid; see _record_paper_fill's docstring."""
        trading_mode.seed_paper_cash(100_000)
        trading_mode.paper_fill("T", "yes", 35, 7, "buy")
        after_buy = trading_mode.paper_cash()

        trading_mode.paper_fill("T", "yes", 1, 7, "sell")

        assert trading_mode.paper_cash() == after_buy

    def test_the_bankroll_survives_a_restart(self):
        trading_mode.seed_paper_cash(100_000)
        trading_mode.adjust_paper_cash(-12_345)

        trading_mode._paper_cash = None  # simulate a fresh process
        trading_mode.load_paper_positions()

        assert trading_mode.paper_cash() == 100_000 - 12_345

    def test_reset_forgets_the_bankroll_not_just_the_positions(self):
        trading_mode.seed_paper_cash(100_000)

        trading_mode.reset_paper_positions()

        assert trading_mode.paper_cash() is None
        # And the forgotten value must not resurrect on the next reload.
        trading_mode.load_paper_positions()
        assert trading_mode.paper_cash() is None

    def test_a_cleared_bankroll_can_be_reseeded(self):
        """0 would look like a seeded, exhausted bankroll and refuse every
        trade; reset must leave it truly unseeded (None)."""
        trading_mode.seed_paper_cash(100_000)
        trading_mode.reset_paper_positions()

        trading_mode.seed_paper_cash(50_000)

        assert trading_mode.paper_cash() == 50_000


class TestPersistenceRetriesALockedDatabase:
    """@retry_sqlite on _persist_paper_positions used to do nothing: its own
    body caught every exception, including sqlite3.OperationalError, before
    the decorator around it ever saw one to retry. The retried step is now
    the raw write (_write_paper_positions / _write_paper_cash); the public
    functions still never raise.
    """

    def test_a_locked_positions_write_is_retried_not_silently_dropped(self, monkeypatch):
        import sqlite3

        calls = {"n": 0}
        real_connect = trading_mode._connect_paper_db

        def flaky_connect():
            calls["n"] += 1
            if calls["n"] == 1:
                raise sqlite3.OperationalError("database is locked")
            return real_connect()

        monkeypatch.setattr(trading_mode, "_connect_paper_db", flaky_connect)

        trading_mode.paper_fill("T", "yes", 35, 7, "buy")

        assert calls["n"] >= 2, "a locked database must be retried, not given up on immediately"
        assert trading_mode.paper_position("T") == 7

    def test_a_locked_cash_write_is_retried_not_silently_dropped(self, monkeypatch):
        import sqlite3

        calls = {"n": 0}
        real_connect = trading_mode._connect_paper_db

        def flaky_connect():
            calls["n"] += 1
            if calls["n"] == 1:
                raise sqlite3.OperationalError("database is locked")
            return real_connect()

        trading_mode.seed_paper_cash(100_000)
        monkeypatch.setattr(trading_mode, "_connect_paper_db", flaky_connect)

        trading_mode.adjust_paper_cash(-1_000)

        assert calls["n"] >= 2
        assert trading_mode.paper_cash() == 99_000
