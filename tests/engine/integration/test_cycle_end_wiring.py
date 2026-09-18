"""CYCLE_END must actually be published, or the exit policy never runs.

Hand.check_exits (stop-loss, take-profit, pre-expiry exit) and
Senses.stop_scan both subscribed to CYCLE_END, and nothing in main.py ever
published it -- main only ever published CYCLE_COMPLETE, which triggers the
next autopilot pulse but has nothing to do with reviewing open positions.
The exit policy never ran, in paper mode or live.

This runs a real cycle through the real engine (agents wired the way
main.initialize_system builds them) rather than asserting on the source text,
so a future refactor that renames the event without updating both ends still
fails this test. block_network (conftest.py, autouse) makes the Kalshi calls
inside check_exits fail fast and get caught by its own try/except, exactly as
they do in production when Kalshi is unreachable.
"""

from unittest.mock import AsyncMock

import pytest
from main import GhostEngine


@pytest.mark.asyncio
async def test_execute_single_cycle_publishes_cycle_end():
    engine = GhostEngine()
    await engine.initialize_system()

    seen = []
    await engine.bus.subscribe("CYCLE_END", lambda msg: seen.append(msg.payload))

    await engine.execute_single_cycle(is_paper_trading=True)

    assert seen, "CYCLE_END must be published at the end of every cycle"
    assert seen[0]["cycle"] == engine.cycle_count


@pytest.mark.asyncio
async def test_cycle_end_reaches_hands_exit_review():
    """Not just published -- Hand's subscriber must actually run.

    check_exits is bound to the bus at subscribe time (setup()), so
    monkeypatching engine.hand.check_exits afterwards would not be seen by
    the dispatcher -- it would only ever call the original function object.
    Instead this replaces an attribute check_exits reads dynamically on
    every call (self.kalshi_client) and confirms it was actually reached.
    """
    engine = GhostEngine()
    await engine.initialize_system()

    fake_client = AsyncMock()
    fake_client.get_positions = AsyncMock(return_value=[])
    engine.hand.kalshi_client = fake_client

    await engine.execute_single_cycle(is_paper_trading=True)

    fake_client.get_positions.assert_awaited()


@pytest.mark.asyncio
async def test_cycle_end_still_publishes_when_the_cycle_raises():
    """Exit review must not depend on the rest of the cycle succeeding.

    CYCLE_END is published from execute_single_cycle's `finally`, precisely
    so a cycle that raised midway still gets its positions reviewed. This
    breaks the TICK publish inside the try body and confirms CYCLE_END fires
    anyway; execute_single_cycle logs the failure rather than re-raising, so
    the call below completes normally either way.
    """
    engine = GhostEngine()
    await engine.initialize_system()

    seen = []
    await engine.bus.subscribe("CYCLE_END", lambda msg: seen.append(msg.payload))

    real_publish = engine.bus.publish

    async def flaky_publish(topic, payload, sender):
        if topic == "TICK":
            raise RuntimeError("simulated cycle failure")
        return await real_publish(topic, payload, sender)

    engine.bus.publish = flaky_publish

    await engine.execute_single_cycle(is_paper_trading=True)

    assert seen, "CYCLE_END must fire even when the cycle body raised"


def test_cycle_end_subscribers_exist():
    """Sanity check that the regression is even reachable: something still
    listens for CYCLE_END. If this ever fails, the wiring test above is
    exercising a topic nobody cares about any more and should be revisited.
    """
    from agents.hand.agent import HandAgent
    from agents.senses.agent import SensesAgent

    assert "check_exits" in dir(HandAgent)
    assert "stop_scan" in dir(SensesAgent)
