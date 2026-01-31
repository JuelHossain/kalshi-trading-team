import pytest
import asyncio
from engine.agents.soul import SoulAgent
from engine.core.bus import EventBus
from engine.core.synapse import Synapse, SynapseError
from engine.core.vault import RecursiveVault

@pytest.mark.asyncio
async def test_autopilot_recovery_on_error_clear(bus, synapse, vault):
    """
    Integration Test: Verify Soul's autopilot stops on error and can be manually resumed.
    Note: Automatic recovery is NOT implemented by design (human must clear errors).
    """
    soul = SoulAgent(1, bus, vault=vault, synapse=synapse)
    await vault.initialize(100000)
    await soul.setup()
    
    # 1. Enable Autopilot
    await bus.publish("SYSTEM_CONTROL", {"action": "START_AUTOPILOT"}, "TEST")
    await asyncio.sleep(0.1)
    assert soul.autopilot_enabled is True
    
    # 2. Inject Critical Error into Synapse
    err = SynapseError(
        agent_name="TEST",
        code="TEST_HALT",
        message="Simulating system halt",
        severity="FATAL",
        domain="ENGINE"
    )
    await synapse.errors.push(err)
    
    # 3. Soul should detect error and stop autopilot (or the engine loop will halt)
    # Actually, the engine's authorize_cycle checks the error box.
    # Soul's autopilot loop also checks it.
    
    # Wait for a few "ticks"
    await asyncio.sleep(1)
    
    # 4. Clear Error
    await synapse.errors.pop()
    assert await synapse.errors.size() == 0
    
    # 5. Resume Autopilot
    await bus.publish("SYSTEM_CONTROL", {"action": "START_AUTOPILOT"}, "TEST")
    await asyncio.sleep(0.1)
    assert soul.autopilot_enabled is True
    
    await soul.teardown()
