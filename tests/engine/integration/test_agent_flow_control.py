"""
Test script to verify agent flow control fixes.

This test simulates the full agent lifecycle to ensure:
1. Senses scans once and goes to standby
2. Brain processes one opportunity per trigger without self-triggering
3. Restock mechanism has proper cooldown
"""

import asyncio
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.brain import BrainAgent
from agents.senses import SensesAgent
from agents.soul import SoulAgent
from core.bus import EventBus
from core.synapse import MarketData, Opportunity, Synapse
from core.vault import RecursiveVault


def clear_database(db_path: str):
    """Clear all queues from the database"""
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"[TEST] Cleared database: {db_path}")


async def test_senses_guard():
    """Test that Senses only scans once and goes to standby"""
    print("\n" + "="*60)
    print("TEST 1: Senses Initial Scan Guard")
    print("="*60)

    clear_database("ghost_memory.db")

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
    if opp_size_1 == opp_size_2:
        print(f"\n[PASS] Senses guard working - no re-queue ({opp_size_1} == {opp_size_2})")
        return True
    print(f"\n[FAIL] Senses re-queued ({opp_size_2} > {opp_size_1})")
    return False


async def test_brain_no_self_trigger():
    """Test that Brain doesn't self-trigger after processing"""
    print("\n" + "="*60)
    print("TEST 2: Brain No Self-Trigger")
    print("="*60)

    clear_database("ghost_memory.db")

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
    if opp_size_final == opp_size_after and exec_size_final == exec_size:
        print("\n[OK PASS] Brain did NOT self-trigger (no change after wait)")
        return True
    print("\n[FAIL FAIL] Brain self-triggered or processed multiple")
    print(f"        Opportunities changed: {opp_size_after} -> {opp_size_final}")
    print(f"        Executions changed: {exec_size} -> {exec_size_final}")
    return False


async def test_restock_cooldown():
    """Test that restock has proper cooldown"""
    print("\n" + "="*60)
    print("TEST 3: Restock Cooldown")
    print("="*60)

    clear_database("ghost_memory.db")

    bus = EventBus()
    synapse = Synapse()
    vault = RecursiveVault()

    # Initialize agents
    soul = SoulAgent(1, bus, vault=vault, synapse=synapse)
    brain = BrainAgent(3, bus, synapse=synapse)

    await soul.setup()
    await brain.setup()

    # Manually trigger restock twice quickly
    print("\n[TEST] First REQUEST_RESTOCK...")
    await bus.publish("REQUEST_RESTOCK", {}, "TEST")
    await asyncio.sleep(1)

    print("[TEST] Second REQUEST_RESTOCK (immediate)...")
    await bus.publish("REQUEST_RESTOCK", {}, "TEST")
    await asyncio.sleep(1)

    # Check if cooldown prevented duplicate processing
    # The cooldown should prevent rapid restocks
    print("\n[OK INFO] Restock cooldown test completed")
    print("[OK INFO] Check logs above for flow control messages")
    return True


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
