"""
Test script to verify agent flow control fixes.

This test simulates the full agent lifecycle to ensure:
1. Brain does not re-trigger itself; its monitor loop drains the queue
2. Restock mechanism has proper cooldown

Senses' own scan-once-then-standby invariant, and the rescan that must
happen once both the stock buffer and the opportunity queue run dry, are
covered in tests/engine/agents/test_senses_rescan.py; that module uses a
fake Kalshi client so it can tell "the guard held" from "there was nothing
to scan" -- this file's former test_senses_guard could not, since it gave
Senses no client at all and so passed unconditionally either way.
"""

import asyncio
import os

import pytest

# NOTE: no sys.path manipulation here. This module previously inserted
# tests/engine at the front of sys.path, which shadowed the real `agents`
# package with the test directory of the same name -- it only imported at all
# because an earlier test had already cached the real module. conftest.py puts
# the engine source on the path.
from agents.brain import BrainAgent
from agents.soul import SoulAgent
from core.bus import EventBus
from core.flow_control import should_restock
from core.synapse import MarketData, Opportunity, Synapse
from core.vault import RecursiveVault


def clear_database(db_path: str):
    """Clear all queues from the database"""
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"[TEST] Cleared database: {db_path}")


async def _settled(read, quiet_for: float = 0.3, timeout: float = 10.0):
    """Wait until `read()` stops changing, then return its value.

    These tests used fixed sleeps -- publish, sleep 2s, measure -- which assumes
    the agents finish within the guess. On a slower machine they do not, so the
    measurement lands mid-processing and the queue keeps draining during the
    window the test believes is quiet. That is how test_brain_no_self_trigger
    failed on CI while passing locally: not a self-trigger, just a stopwatch.

    Polls until the value has held steady for `quiet_for` seconds, so the test
    waits exactly as long as the work takes and no longer.
    """
    deadline = asyncio.get_event_loop().time() + timeout
    previous = await read()
    stable_since = asyncio.get_event_loop().time()

    while asyncio.get_event_loop().time() < deadline:
        await asyncio.sleep(0.05)
        current = await read()
        now = asyncio.get_event_loop().time()
        if current != previous:
            previous, stable_since = current, now
        elif now - stable_since >= quiet_for:
            return current

    return previous


@pytest.mark.asyncio
async def test_brain_does_not_retrigger_itself():
    """The Brain must not publish the event that wakes it.

    This asserted that the opportunity queue stops changing after a trigger,
    on the premise that the Brain "processes exactly 1 opportunity per
    trigger". That is not the design: monitor_queue is documented as a
    CONTINUOUS MONITORING LOOP that "processes ALL items until empty", so a
    draining queue is the Brain working, not misbehaving.

    The assertion was unfalsifiable before -- the function signalled its result
    with `return False`, which pytest ignores -- so the mismatch went unnoticed
    until it was converted to a real assertion, at which point it failed on CI
    whenever the runner was slow enough for the measurement to land mid-drain.

    A self-trigger would mean the Brain publishing OPPORTUNITIES_READY itself
    and looping forever. That is what this now checks, alongside the behaviour
    the design actually promises.
    """
    print("\n" + "=" * 60)
    print("TEST 2: Brain Does Not Re-Trigger Itself")
    print("=" * 60)

    clear_database(os.environ["GHOST_SYNAPSE_DB"])

    bus = EventBus()
    synapse = Synapse()
    vault = RecursiveVault()

    soul = SoulAgent(1, bus, vault=vault, synapse=synapse)
    brain = BrainAgent(3, bus, synapse=synapse)

    await soul.setup()
    await brain.setup()

    # Record every OPPORTUNITIES_READY, and who sent it.
    senders = []

    async def record(message):
        senders.append(message.sender)

    await bus.subscribe("OPPORTUNITIES_READY", record)

    for i in range(3):
        await synapse.opportunities.push(
            Opportunity(
                ticker=f"TEST{i}",
                market_data=MarketData(
                    ticker=f"TEST{i}",
                    title=f"Test Market {i}",
                    subtitle="Test",
                    yes_price=50,
                    no_price=50,
                    volume=10000,
                    expiration="2025-01-30",
                ),
            )
        )

    await bus.publish("OPPORTUNITIES_READY", {"count": 3, "source": "SENSES"}, "TEST")

    remaining = await _settled(synapse.opportunities.size, quiet_for=1.0)
    print(f"[TEST] Opportunities remaining once settled: {remaining}")
    print(f"[TEST] OPPORTUNITIES_READY senders seen: {senders}")

    assert (
        brain.name not in senders
    ), f"Brain published its own trigger, which would loop forever: {senders}"
    assert (
        remaining == 0
    ), f"the monitor loop is meant to drain the queue to empty, left {remaining}"


@pytest.mark.asyncio
async def test_restock_cooldown():
    """Restock is refused until the cooldown window has elapsed.

    Previously this published two bus events, asserted nothing, printed
    "check logs above" and returned True -- it could never fail. should_restock
    is a pure function, so the cooldown is asserted directly instead.
    """
    synapse = Synapse()
    now = 1_000_000.0
    over_threshold = 5  # veto_threshold

    # Inside the 60s window: refused even with enough vetoes.
    assert not await should_restock(
        synapse, over_threshold, last_restock_time=now - 59, current_time=now
    )

    # Outside the window: allowed.
    assert await should_restock(
        synapse, over_threshold, last_restock_time=now - 61, current_time=now
    )

    # Boundary: exactly the cooldown is allowed (the check is strict <).
    assert await should_restock(
        synapse, over_threshold, last_restock_time=now - 60, current_time=now
    )

    # Too few vetoes is refused regardless of elapsed time.
    assert not await should_restock(
        synapse, over_threshold - 1, last_restock_time=now - 9999, current_time=now
    )
