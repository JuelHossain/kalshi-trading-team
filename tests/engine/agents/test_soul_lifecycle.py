import asyncio

import pytest
from core.shared_utils import fire_and_forget

from engine.agents.soul import SoulAgent


@pytest.mark.asyncio
async def test_soul_initialization_state(bus, synapse, vault):
    """Verify Soul agent initializes with correct defaults."""
    soul = SoulAgent(1, bus, vault=vault, synapse=synapse)
    assert soul.agent_id == 1
    assert soul.name == "SOUL"
    assert soul.autopilot_enabled is False
    assert soul.is_locked_down is False


@pytest.mark.asyncio
async def test_soul_autopilot_toggle(bus, synapse, vault):
    """Verify Soul agent responds to START/STOP_AUTOPILOT messages."""
    soul = SoulAgent(1, bus, vault=vault, synapse=synapse)
    await soul.start()

    # 1. Start Autopilot
    await bus.publish(
        "SYSTEM_CONTROL", {"action": "START_AUTOPILOT", "isPaperTrading": True}, "TEST"
    )
    await asyncio.sleep(0.1)
    assert soul.autopilot_enabled is True

    # 2. Stop Autopilot
    await bus.publish("SYSTEM_CONTROL", {"action": "STOP_AUTOPILOT"}, "TEST")
    await asyncio.sleep(0.1)
    assert soul.autopilot_enabled is False

    await soul.teardown()


class _FakeEngine:
    """The slice of main.GhostEngine that autopilot drives.

    Mirrors _handle_cycle_request: the cycle is detached with fire_and_forget
    from inside the REQUEST_CYCLE dispatch, refused while one is running, and
    publishes CYCLE_COMPLETE when it ends.
    """

    def __init__(self, bus):
        self.bus = bus
        self.is_processing = False
        self.cycles = 0

    async def on_request(self, message):
        if not self.is_processing:
            fire_and_forget(self.run_cycle())

    async def run_cycle(self):
        self.is_processing = True
        try:
            await asyncio.sleep(0)
            self.cycles += 1
        finally:
            self.is_processing = False
        await self.bus.publish("CYCLE_COMPLETE", {"cycle": self.cycles}, "GHOST")


async def _autopilot(bus, synapse, vault, delay):
    soul = SoulAgent(1, bus, vault=vault, synapse=synapse)
    soul.autopilot_delay = delay
    await soul.start()
    engine = _FakeEngine(bus)
    await bus.subscribe("REQUEST_CYCLE", engine.on_request)
    return soul, engine


async def _wait_for(predicate, timeout=2.0):
    for _ in range(int(timeout / 0.01)):
        if predicate():
            return True
        await asyncio.sleep(0.01)
    return predicate()


async def _start(bus):
    await bus.publish(
        "SYSTEM_CONTROL", {"action": "START_AUTOPILOT", "isPaperTrading": True}, "TEST"
    )


@pytest.mark.asyncio
async def test_autopilot_keeps_cycling(bus, synapse, vault):
    """Autopilot must keep requesting cycles, not stop after the first.

    Regression for a live stall on 2026-09-18: the cycle task was detached
    from inside the REQUEST_CYCLE dispatch and inherited the bus's re-entrancy
    guard, so the Soul's next REQUEST_CYCLE from under it was dropped. The
    engine ran one cycle and sat idle for hours with autopilot "enabled".
    """
    soul, engine = await _autopilot(bus, synapse, vault, delay=0.02)
    await _start(bus)

    assert await _wait_for(lambda: engine.cycles >= 3), f"stalled after {engine.cycles} cycle(s)"
    assert bus.reentrant_drops == 0
    await soul.teardown()


@pytest.mark.asyncio
async def test_manual_cycle_does_not_start_a_second_pulse_chain(bus, synapse, vault):
    """A cycle completing while a pulse waits must replace it, not add another.

    Otherwise every manual /trigger during autopilot permanently doubles the
    cadence: two chains, each re-arming itself.
    """
    soul, engine = await _autopilot(bus, synapse, vault, delay=0.15)
    await _start(bus)
    assert await _wait_for(lambda: engine.cycles >= 1)

    # A manual trigger lands while the pulse is waiting.
    await bus.publish("REQUEST_CYCLE", {"isPaperTrading": True}, "OPERATOR")
    assert await _wait_for(lambda: engine.cycles >= 2)

    before = engine.cycles
    await asyncio.sleep(0.15 * 3 + 0.05)
    gained = engine.cycles - before
    await soul.teardown()

    # One chain yields ~3 cycles in 3 delays; two chains would yield ~6.
    assert gained <= 4, f"{gained} cycles in 3 pulse delays: a second chain is running"


@pytest.mark.asyncio
async def test_stop_and_teardown_cancel_the_pending_pulse(bus, synapse, vault):
    """No cycle may be requested after STOP_AUTOPILOT or teardown."""
    soul, engine = await _autopilot(bus, synapse, vault, delay=0.05)
    await _start(bus)
    assert await _wait_for(lambda: engine.cycles >= 1)

    await bus.publish("SYSTEM_CONTROL", {"action": "STOP_AUTOPILOT"}, "TEST")
    stopped_at = engine.cycles
    await asyncio.sleep(0.2)
    assert engine.cycles == stopped_at, "a pulse fired after STOP_AUTOPILOT"

    await _start(bus)
    assert await _wait_for(lambda: engine.cycles > stopped_at)
    await soul.teardown()
    # A cycle in flight at teardown completes afterwards; it must not re-arm.
    await asyncio.sleep(0.02)
    torn_down_at = engine.cycles
    await asyncio.sleep(0.2)
    assert engine.cycles == torn_down_at, "a pulse fired after teardown"
    assert soul._pulse_task is None
