import pytest
import asyncio
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
    await bus.publish("SYSTEM_CONTROL", {"action": "START_AUTOPILOT", "isPaperTrading": True}, "TEST")
    await asyncio.sleep(0.1)
    assert soul.autopilot_enabled is True
    
    # 2. Stop Autopilot
    await bus.publish("SYSTEM_CONTROL", {"action": "STOP_AUTOPILOT"}, "TEST")
    await asyncio.sleep(0.1)
    assert soul.autopilot_enabled is False
    
    await soul.teardown()
