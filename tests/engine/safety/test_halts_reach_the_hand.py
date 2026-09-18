"""Every halt must stop new positions, not just new cycles.

The kill switch, Ragnarok, a Soul lockdown and the error box were read only by
authorize_cycle. The Brain's queue loop and the Hand run independently of
cycles, so an approval already queued went straight to an order with every
halt engaged -- the audit reproduced "ORDER EXECUTED" with the kill switch set,
right after Ragnarok had flattened. And the live switch was armed before
authorize_cycle ran, so a refused cycle could still arm real orders.

The halt lives in core.trading_mode and is enforced in place_order for buys
only: exits and Ragnarok's own closes must keep working while halted.
"""

import pytest
from core import trading_mode
from core.network import KalshiClient
from core.synapse import Synapse
from http_api.routes import (
    activate_kill_switch,
    deactivate_kill_switch,
    reset_system,
    trigger_ragnarok,
)


@pytest.fixture
def client():
    """A KalshiClient whose transport fails loudly if anything reaches it."""
    c = KalshiClient.__new__(KalshiClient)

    async def _explode(*args, **kwargs):
        raise AssertionError("a request reached Kalshi")

    c.request = _explode
    return c


class TestPlaceOrderHonoursTheHalt:
    @pytest.mark.asyncio
    async def test_a_buy_is_refused_while_halted(self, client):
        trading_mode.halt("kill_switch", "manual kill switch")

        with pytest.raises(RuntimeError, match="halted"):
            await client.place_order("KXA", "yes", "limit", 40, 5, action="buy")

    @pytest.mark.asyncio
    async def test_a_sell_still_goes_through_while_halted(self, client):
        """Exits and Ragnarok's closes are sells; a halt must not trap a position."""
        trading_mode.halt("kill_switch", "manual kill switch")

        result = await client.place_order("KXA", "yes", "limit", 1, 5, action="sell")

        assert result["paper"] is True and result["action"] == "sell"

    @pytest.mark.asyncio
    async def test_the_env_kill_switch_is_a_halt_too(self, client, monkeypatch):
        monkeypatch.setenv("KILL_SWITCH", "true")

        with pytest.raises(RuntimeError, match="KILL_SWITCH"):
            await client.place_order("KXA", "yes", "limit", 40, 5, action="buy")

    @pytest.mark.asyncio
    async def test_buys_work_again_once_lifted(self, client):
        trading_mode.halt("kill_switch", "manual kill switch")
        trading_mode.unhalt("kill_switch")

        result = await client.place_order("KXA", "yes", "limit", 40, 5, action="buy")

        assert result["paper"] is True


class _Bus:
    def __init__(self):
        self.published = []

    async def publish(self, topic, payload, sender):
        self.published.append((topic, payload))


class _Vault:
    def release_all_reservations(self):
        pass


class _Engine:
    def __init__(self, synapse):
        self.manual_kill_switch = False
        self.is_processing = False
        self.running = True
        self.cycle_count = 3
        self.last_cycle_time = None
        self.bus = _Bus()
        self.vault = _Vault()
        self.synapse = synapse
        self.soul = None


@pytest.fixture
def engine(tmp_path):
    return _Engine(Synapse(db_path=str(tmp_path / "halts.db")))


class TestTheRoutesSetAndLiftIt:
    @pytest.mark.asyncio
    async def test_kill_switch_halts_disarms_and_stops_autopilot(self, engine):
        trading_mode.set_live(True)

        await activate_kill_switch(engine)(None)

        assert trading_mode.is_halted()
        assert trading_mode.is_live() is False
        assert ("SYSTEM_CONTROL", {"action": "STOP_AUTOPILOT"}) in engine.bus.published

    @pytest.mark.asyncio
    async def test_deactivating_lifts_it(self, engine):
        await activate_kill_switch(engine)(None)
        await deactivate_kill_switch(engine)(None)

        assert not trading_mode.is_halted()

    @pytest.mark.asyncio
    async def test_reset_lifts_every_halt(self, engine):
        trading_mode.halt("kill_switch", "manual kill switch")
        trading_mode.halt("cycle_gate", "ERROR BOX ACTIVE")

        await reset_system(engine)(None)

        assert not trading_mode.is_halted()

    @pytest.mark.asyncio
    async def test_ragnarok_halts_and_drops_stale_approvals(self, engine, monkeypatch):
        import core.safety
        from core.synapse import ExecutionSignal, MarketData, Opportunity

        async def fake_ragnarok():
            return {
                "orders_found": 2,
                "orders_cancelled": 2,
                "positions_found": 1,
                "positions_closed": 1,
            }

        monkeypatch.setattr(core.safety, "execute_ragnarok", fake_ragnarok)
        opp = Opportunity(
            ticker="KXA",
            market_data=MarketData(
                ticker="KXA",
                title="t",
                subtitle="s",
                yes_price=50,
                no_price=50,
                volume=1000,
                expiration="2099-01-01",
            ),
        )
        await engine.synapse.executions.push(
            ExecutionSignal(
                target_opportunity=opp,
                action="BUY",
                side="YES",
                confidence=0.9,
                monte_carlo_ev=0.1,
                reasoning="approved before the emergency",
                suggested_count=5,
            )
        )
        trading_mode.set_live(True)

        response = await trigger_ragnarok(engine)(None)

        assert trading_mode.is_halted()
        assert trading_mode.is_live() is False
        assert await engine.synapse.executions.size() == 0
        assert engine.manual_kill_switch is True
        body = response.text
        assert "closed 1/1 positions" in body and "Vault locked" not in body


class TestTheCycleGate:
    @pytest.mark.asyncio
    async def test_a_refused_cycle_never_arms_live_orders(self, monkeypatch):
        """set_live used to run before authorize_cycle, so a /trigger with
        isPaperTrading=false armed real placement even when the kill switch
        refused the cycle."""
        from main import GhostEngine

        monkeypatch.delenv("IS_PAPER_TRADING", raising=False)
        engine = GhostEngine()
        await engine.initialize_system()
        engine.manual_kill_switch = True

        await engine.execute_single_cycle(is_paper_trading=False)

        assert trading_mode.is_live() is False
        assert trading_mode.halted_by("cycle_gate"), "the refusal must reach the Hand too"

    @pytest.mark.asyncio
    async def test_the_brain_leaves_the_queue_alone_while_halted(self, tmp_path):
        import asyncio
        import os
        from unittest.mock import patch

        from agents.brain import BrainAgent
        from core.bus import EventBus
        from core.synapse import MarketData, Opportunity

        synapse = Synapse(db_path=str(tmp_path / "brain_halt.db"))
        await synapse.opportunities.push(
            Opportunity(
                ticker="KXA",
                market_data=MarketData(
                    ticker="KXA",
                    title="t",
                    subtitle="s",
                    yes_price=50,
                    no_price=50,
                    volume=1000,
                    expiration="2099-01-01",
                ),
            )
        )
        trading_mode.halt("kill_switch", "manual kill switch")
        with patch.dict(os.environ, {}, clear=True):
            brain = BrainAgent(3, EventBus(), synapse=synapse)
        await brain.setup()

        await asyncio.sleep(1.5)
        assert await synapse.opportunities.size() == 1, "halted: nothing may be analysed"

        brain.stop_requested = True
        brain._monitoring_task.cancel()
