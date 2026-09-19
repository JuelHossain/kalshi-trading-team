"""The paper soak cannot measure P&L unless something calls record_settlement.

record_settlement (core/ledger.py) existed only for tests to call directly.
Hand publishes TRADE_RESULT with outcome "pending" and never anything else,
research/settle.py writes to a different database entirely, and nothing else
in the engine ever asked Kalshi whether a held market had resolved. Every
fill's pnl_cents stayed None forever, calibration() had nothing to measure,
and realised_edge() reported n=0 no matter how long a soak ran.

Hand.settle_positions closes that gap: on every CYCLE_END, it asks Kalshi
about every ticker with a fill and no settlement yet, and records the answer.
"""

from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from agents.hand import HandAgent
from core import ledger, trading_mode
from core.vault import RecursiveVault


@pytest.fixture(autouse=True)
def clean_paper_book():
    trading_mode.reset_paper_positions()
    yield
    trading_mode.reset_paper_positions()


def _approved_fill(ticker, market_price=0.5, side="yes", price_cents=50, stake=200):
    ledger.record_decision(
        ticker, market_price, outcome="APPROVED", estimated_probability=market_price + 0.1
    )
    ledger.record_fill(
        ticker,
        stake,
        f"kalshi-order-{ticker}",
        side=side,
        price_cents=price_cents,
        count=stake // price_cents,
    )


def _settled_yes(ticker):
    with ledger._connect() as conn:
        row = conn.execute(
            "SELECT settled_yes FROM decisions WHERE ticker = ?", (ticker,)
        ).fetchone()
    return row[0] if row else None


@pytest_asyncio.fixture
async def hand():
    vault = RecursiveVault(test_mode=True)
    await vault.initialize(100_000)
    return HandAgent(4, bus=AsyncMock(), vault=vault, kalshi_client=AsyncMock())


class TestSettlementIsRecorded:
    @pytest.mark.asyncio
    async def test_the_regression_a_resolved_market_is_recorded(self, hand):
        """The whole point: a settled market's outcome reaches the ledger."""
        _approved_fill("A")
        hand.kalshi_client.get_market = AsyncMock(
            return_value={"status": "settled", "result": "yes"}
        )

        settled = await hand.settle_positions()

        assert settled == 1
        assert _settled_yes("A") == 1

    @pytest.mark.asyncio
    async def test_a_no_result_is_recorded_as_zero(self, hand):
        _approved_fill("B")
        hand.kalshi_client.get_market = AsyncMock(
            return_value={"status": "finalized", "result": "no"}
        )

        await hand.settle_positions()

        assert _settled_yes("B") == 0

    @pytest.mark.asyncio
    async def test_a_still_open_market_is_left_unsettled(self, hand):
        _approved_fill("C")
        hand.kalshi_client.get_market = AsyncMock(return_value={"status": "open", "result": ""})

        settled = await hand.settle_positions()

        assert settled == 0
        assert _settled_yes("C") is None

    @pytest.mark.asyncio
    async def test_only_unsettled_fills_are_checked(self, hand):
        _approved_fill("D")
        ledger.record_settlement("D", settled_yes=True)  # already settled
        hand.kalshi_client.get_market = AsyncMock(
            side_effect=AssertionError("should not be called")
        )

        settled = await hand.settle_positions()

        assert settled == 0

    @pytest.mark.asyncio
    async def test_a_lookup_failure_does_not_raise(self, hand):
        """check_exits and settle_positions both run on CYCLE_END: one must
        not be able to take the other down."""
        _approved_fill("E")
        hand.kalshi_client.get_market = AsyncMock(side_effect=RuntimeError("network down"))

        settled = await hand.settle_positions()

        assert settled == 0
        assert _settled_yes("E") is None

    @pytest.mark.asyncio
    async def test_no_kalshi_client_is_a_no_op(self):
        vault = RecursiveVault(test_mode=True)
        await vault.initialize(100_000)
        hand = HandAgent(4, bus=AsyncMock(), vault=vault, kalshi_client=None)
        _approved_fill("F")

        assert await hand.settle_positions() == 0
        assert _settled_yes("F") is None


class TestSettlementClearsThePaperBook:
    @pytest.mark.asyncio
    async def test_a_settled_ticker_is_removed_from_the_paper_book(self, hand):
        """A settled market cannot be traded again; has_open_position and
        check_exits must not go on treating it as held."""
        trading_mode.paper_fill("G", "yes", 40, 5, "buy")
        _approved_fill("G", side="yes", price_cents=40, stake=200)
        hand.kalshi_client.get_market = AsyncMock(
            return_value={"status": "settled", "result": "yes"}
        )

        await hand.settle_positions()

        assert trading_mode.paper_position("G") == 0


class TestSettlementCreditsTheBankroll:
    """settle_paper_position already computed the payout; settle_positions
    used to throw it away, so a paper win zeroed the holding without ever
    growing the bankroll that measures whether the strategy works."""

    @pytest.mark.asyncio
    async def test_a_winning_settlement_credits_a_dollar_a_contract(self, hand):
        trading_mode.seed_paper_cash(100_000)
        trading_mode.paper_fill("H", "yes", 40, 5, "buy")
        assert trading_mode.paper_cash() == 100_000 - 200
        _approved_fill("H", side="yes", price_cents=40, stake=200)
        hand.kalshi_client.get_market = AsyncMock(
            return_value={"status": "settled", "result": "yes"}
        )

        await hand.settle_positions()

        assert trading_mode.paper_cash() == 100_000 - 200 + 500  # 5 contracts x $1

    @pytest.mark.asyncio
    async def test_a_losing_settlement_credits_nothing(self, hand):
        trading_mode.seed_paper_cash(100_000)
        trading_mode.paper_fill("I", "yes", 40, 5, "buy")
        after_buy = trading_mode.paper_cash()
        _approved_fill("I", side="yes", price_cents=40, stake=200)
        hand.kalshi_client.get_market = AsyncMock(
            return_value={"status": "settled", "result": "no"}
        )

        await hand.settle_positions()

        assert trading_mode.paper_cash() == after_buy
