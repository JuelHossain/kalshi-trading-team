"""The Brain -> Hand trade cycle, driven end to end against a mocked market.

The repository's only end-to-end test, test_full_trade_loop_flow, asserts
nothing at all -- it prints, and its own comment says "We don't strictly assert
balance decrease". It also depends on the k_client fixture, so it skips
entirely without live demo credentials. The trade path therefore had no
coverage that could fail.

These tests drive the real decision path with a mocked Kalshi client and a
mocked AI debate, so they run anywhere, need no credentials, and assert what
actually happened -- including the safety rules refusing a trade.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from agents.brain import BrainAgent
from agents.hand import HandAgent
from core.bus import EventBus
from core.synapse import Synapse
from core.vault import RecursiveVault


def _opportunity(ticker="KXTEST-01", **over):
    opp = {
        "ticker": ticker,
        "title": "Integration test market",
        "yes_price": 50,
        "no_price": 50,
        "volume": 10000,
        "timestamp": datetime.now().isoformat(),
    }
    opp.update(over)
    return opp


def _debate(confidence=0.95, probability=0.80):
    return AsyncMock(
        return_value={
            "estimated_probability": probability,
            "confidence": confidence,
            "reasoning": "integration test",
        }
    )


@pytest.fixture
def cycle(test_db):
    """A Brain and Hand wired to one bus, one synapse and a funded vault."""
    bus = EventBus()
    synapse = Synapse(db_path=test_db)
    vault = RecursiveVault(test_mode=True)

    kalshi = AsyncMock()
    kalshi.get_balance = AsyncMock(return_value=100_000)  # $1000
    kalshi.get_orderbook = AsyncMock(
        return_value={
            "bids": [{"price": 48, "count": 400}],
            "asks": [{"price": 51, "count": 400}],
        }
    )
    kalshi.place_order = AsyncMock(return_value={"order_id": "integration-order-1"})

    brain = BrainAgent(3, bus, synapse=synapse)
    hand = HandAgent(4, bus, vault=vault, kalshi_client=kalshi, synapse=synapse)
    return {
        "bus": bus, "synapse": synapse, "vault": vault,
        "kalshi": kalshi, "brain": brain, "hand": hand,
    }


class TestApprovedTradeReachesTheMarket:
    @pytest.mark.asyncio
    async def test_a_confident_opportunity_becomes_a_placed_order(self, cycle):
        """Brain approves -> Synapse carries the signal -> Hand places the order."""
        brain, hand, vault = cycle["brain"], cycle["hand"], cycle["vault"]
        await vault.initialize(100_000)

        brain.run_debate = _debate()
        await brain.process_single_opportunity(_opportunity())

        # The Brain's decision survived into the execution queue.
        assert await cycle["synapse"].executions.size() == 1, "Brain did not queue an execution"

        await hand.on_execution_ready(None)

        cycle["kalshi"].place_order.assert_awaited_once()
        placed = cycle["kalshi"].place_order.await_args.kwargs
        assert placed["ticker"] == "KXTEST-01"
        assert 1 <= placed["price"] <= 99, f"nonsensical order price {placed['price']}"
        assert placed["count"] >= 1, "order placed for zero contracts"

    @pytest.mark.asyncio
    async def test_execution_ready_is_published_for_the_hand(self, cycle):
        """The Hand listens for this event; without it nothing ever trades."""
        seen = []

        async def capture(payload, *_a, **_k):
            seen.append(payload)

        await cycle["bus"].subscribe("EXECUTION_READY", capture)
        cycle["brain"].run_debate = _debate()

        await cycle["brain"].process_single_opportunity(_opportunity())

        assert seen, "EXECUTION_READY never fired, so the Hand would never act"


class TestSafetyRulesRefuseTheTrade:
    """Each of these must stop the cycle before an order is placed."""

    @pytest.mark.asyncio
    async def test_stale_market_data_is_not_traded(self, cycle):
        cycle["brain"].run_debate = _debate()
        old = (datetime.now() - timedelta(seconds=120)).isoformat()

        result = await cycle["brain"].process_single_opportunity(
            _opportunity(timestamp=old)
        )

        assert result == "STALE"
        assert await cycle["synapse"].executions.size() == 0

    @pytest.mark.asyncio
    async def test_zero_ai_confidence_skips_simulation_entirely(self, cycle):
        """Zero confidence must short-circuit before the Monte Carlo runs.

        Asserting the return value alone is not enough: process_single_opportunity
        returns "VETOED" from two different places -- this early guard and the
        final confidence/variance rejection -- so a test that only checks the
        string still passes with the guard deleted. The observable difference is
        whether the simulation ran at all.
        """
        brain = cycle["brain"]
        brain.run_debate = _debate(confidence=0.0)

        with patch.object(brain, "run_simulation", wraps=brain.run_simulation) as sim:
            result = await brain.process_single_opportunity(_opportunity())

        assert result == "VETOED"
        assert not sim.called, "simulation ran despite zero confidence"
        assert await cycle["synapse"].executions.size() == 0

    @pytest.mark.asyncio
    async def test_confidence_below_threshold_does_not_trade(self, cycle):
        brain = cycle["brain"]
        brain.run_debate = _debate(confidence=brain.CONFIDENCE_THRESHOLD - 0.01)

        await brain.process_single_opportunity(_opportunity())

        assert await cycle["synapse"].executions.size() == 0

    @pytest.mark.asyncio
    async def test_edge_below_the_minimum_does_not_trade(self, cycle):
        """Replaces the old variance veto, which could never bind.

        Variance of a binary outcome is p(1-p), maximum 0.25, and the veto
        tested for more than 0.25. Edge is the quantity that decides whether a
        trade is worth taking, and a floor on it can actually reject one.
        """
        brain = cycle["brain"]
        # Price 0.50, estimate 0.52 -> edge 0.02, under the 0.05 minimum.
        brain.run_debate = _debate(probability=0.52)

        await brain.process_single_opportunity(
            _opportunity(kalshi_price=0.50)
        )

        assert await cycle["synapse"].executions.size() == 0

    @pytest.mark.asyncio
    async def test_edge_at_the_minimum_does_trade(self, cycle):
        """The boundary is inclusive, so a trade exactly at the floor is taken."""
        brain = cycle["brain"]
        brain.run_debate = _debate(probability=0.50 + brain.MIN_EDGE)

        await brain.process_single_opportunity(
            _opportunity(kalshi_price=0.50)
        )

        assert await cycle["synapse"].executions.size() == 1

    @pytest.mark.asyncio
    async def test_balance_below_the_hard_floor_blocks_the_order(self, cycle):
        """The Hand must refuse even a signal the Brain approved.

        Asserts the specific error, not merely that no order was placed -- an
        order can fail to appear for many unrelated reasons, and a test that
        only checks its absence passes for all of them.

        Note the mechanism: HARD_FLOOR_CENTS is 25500 and the kill switch trips
        at PRINCIPAL_CAPITAL_CENTS * 0.85, which is also 25500. The thresholds
        coincide, so the kill switch always fires first and execute_order's own
        hard-floor branch is unreachable by balance alone. The trade is stopped
        either way; this records which rule actually does it.
        """
        vault, hand = cycle["vault"], cycle["hand"]
        await vault.initialize(vault.HARD_FLOOR_CENTS - 100)

        cycle["brain"].run_debate = _debate()
        await cycle["brain"].process_single_opportunity(_opportunity())
        await hand.on_execution_ready(None)

        cycle["kalshi"].place_order.assert_not_awaited()
        result = await hand.execute_order("KXTEST-01", 50, 1000)
        assert result["success"] is False
        assert "kill switch" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_hard_floor_branch_refuses_when_reached_directly(self, cycle):
        """Exercise the hard-floor branch itself, past the kill switch.

        Since the two thresholds coincide, the only way to reach this branch is
        to hold the kill switch open while the balance sits below the floor.
        """
        vault, hand = cycle["vault"], cycle["hand"]
        await vault.initialize(100_000)
        vault.current_balance = vault.HARD_FLOOR_CENTS - 1
        vault.kill_switch_active = False

        result = await hand.execute_order("KXTEST-01", 50, 1000)

        assert result["success"] is False
        assert "hard floor" in result["error"].lower()
        cycle["kalshi"].place_order.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_kill_switch_blocks_the_order(self, cycle):
        vault, hand = cycle["vault"], cycle["hand"]
        await vault.initialize(100_000)
        vault.kill_switch_active = True

        cycle["brain"].run_debate = _debate()
        await cycle["brain"].process_single_opportunity(_opportunity())
        await hand.on_execution_ready(None)

        cycle["kalshi"].place_order.assert_not_awaited()
