import asyncio

import pytest

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


@pytest.mark.asyncio
async def test_autopilot_pulses_again_after_cycle_complete(bus, synapse, vault):
    """Autopilot must keep requesting cycles, not stop after the first.

    Regression for a live stall: CYCLE_COMPLETE is published from inside the
    dispatch of the REQUEST_CYCLE that began the cycle, so the Soul's re-pulse
    was a re-entrant publish and the bus dropped it. The engine then ran one
    cycle and sat idle forever with autopilot reporting enabled.
    """
    soul = SoulAgent(1, bus, vault=vault, synapse=synapse)
    soul.autopilot_delay = 0.02
    await soul.start()

    requests = []

    async def record(message):
        requests.append(message.sender)

    async def finish_cycle(message):
        # The engine completes the cycle beneath the REQUEST_CYCLE dispatch.
        await bus.publish("CYCLE_COMPLETE", {}, "TEST")

    await bus.subscribe("REQUEST_CYCLE", record)
    await bus.subscribe("REQUEST_CYCLE", finish_cycle)

    await bus.publish(
        "SYSTEM_CONTROL", {"action": "START_AUTOPILOT", "isPaperTrading": True}, "TEST"
    )
    for _ in range(50):
        if requests.count(soul.name) >= 3:
            break
        await asyncio.sleep(0.02)

    await soul.teardown()

    assert requests.count(soul.name) >= 3, f"autopilot stalled after {requests}"
    assert bus.reentrant_drops == 0, "the pulse must not be published re-entrantly"
