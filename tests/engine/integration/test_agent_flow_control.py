"""
Test script to verify agent flow control fixes.

This test simulates the full agent lifecycle to ensure:
1. Senses scans once and goes to standby
2. Brain processes one opportunity per trigger without self-triggering
3. Restock mechanism has proper cooldown
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
from agents.senses import SensesAgent
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


@pytest.mark.asyncio
async def test_senses_guard():
    """Test that Senses only scans once and goes to standby"""
    print("\n" + "="*60)
    print("TEST 1: Senses Initial Scan Guard")
    print("="*60)

    clear_database(os.environ["GHOST_SYNAPSE_DB"])

    bus = EventBus()
    synapse = Synapse()
    vault = RecursiveVault()

    # Initialize agents
    soul = SoulAgent(1, bus, vault=vault, synapse=synapse)
    senses = SensesAgent(2, bus, kalshi_client=None, synapse=synapse)
    brain = BrainAgent(3, bus, synapse=synapse)

    await soul.setup()
    await senses.setup()
    await brain.setup()

    # First trigger - should queue opportunities
    print("\n[TEST] First PREFLIGHT_COMPLETE trigger...")
    await bus.publish("PREFLIGHT_COMPLETE", {}, "TEST")
    await asyncio.sleep(1)

    opp_size_1 = await synapse.opportunities.size()
    print(f"[TEST] Opportunities after first trigger: {opp_size_1}")

    # Second trigger - should NOT queue more
    print("\n[TEST] Second PREFLIGHT_COMPLETE trigger...")
    await bus.publish("PREFLIGHT_COMPLETE", {}, "TEST")
    await asyncio.sleep(1)

    opp_size_2 = await synapse.opportunities.size()
    print(f"[TEST] Opportunities after second trigger: {opp_size_2}")

    # Verify guard is working
    assert opp_size_1 == opp_size_2, (
        f"Senses re-queued on a second PREFLIGHT_COMPLETE: {opp_size_1} -> {opp_size_2}"
    )


@pytest.mark.asyncio
async def test_brain_no_self_trigger():
    """Test that Brain doesn't self-trigger after processing"""
    print("\n" + "="*60)
    print("TEST 2: Brain No Self-Trigger")
    print("="*60)

    clear_database(os.environ["GHOST_SYNAPSE_DB"])

    bus = EventBus()
    synapse = Synapse()
    vault = RecursiveVault()

    # Initialize agents
    soul = SoulAgent(1, bus, vault=vault, synapse=synapse)
    brain = BrainAgent(3, bus, synapse=synapse)

    await soul.setup()
    await brain.setup()

    # Manually add some test opportunities
    print("\n[TEST] Adding 3 test opportunities...")
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

    opp_size_initial = await synapse.opportunities.size()
    print(f"[TEST] Initial opportunities: {opp_size_initial}")

    # Trigger Brain processing
    print("\n[TEST] Triggering OPPORTUNITIES_READY...")
    await bus.publish("OPPORTUNITIES_READY", {"count": opp_size_initial, "source": "SENSES"}, "TEST")
    await asyncio.sleep(2)

    opp_size_after = await synapse.opportunities.size()
    exec_size = await synapse.executions.size()

    print(f"[TEST] Opportunities after processing: {opp_size_after}")
    print(f"[TEST] Executions queued: {exec_size}")

    # Wait to check for self-trigger
    print("\n[TEST] Waiting 3 seconds to check for self-trigger...")
    await asyncio.sleep(3)

    opp_size_final = await synapse.opportunities.size()
    exec_size_final = await synapse.executions.size()

    print(f"[TEST] Final opportunities: {opp_size_final}")
    print(f"[TEST] Final executions: {exec_size_final}")

    # Brain should process exactly 1 opportunity per trigger
    assert opp_size_final == opp_size_after, (
        f"Brain self-triggered: opportunities changed {opp_size_after} -> {opp_size_final}"
    )
    assert exec_size_final == exec_size, (
        f"Brain self-triggered: executions changed {exec_size} -> {exec_size_final}"
    )


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


async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("AGENT FLOW CONTROL TEST SUITE")
    print("="*60)

    results = []

    # Run tests
    results.append(("Senses Guard", await test_senses_guard()))
    results.append(("Brain No Self-Trigger", await test_brain_no_self_trigger()))
    results.append(("Restock Cooldown", await test_restock_cooldown()))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    for test_name, passed in results:
        status = "OK PASS" if passed else "FAIL FAIL"
        print(f"{status}: {test_name}")

    total = len(results)
    passed = sum(1 for _, p in results if p)

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n[OK SUCCESS] All flow control tests passed!")
        return 0
    print(f"\n[FAIL FAILURE] {total - passed} test(s) failed")
    return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
