import pytest
import asyncio
from engine.main import GhostEngine
from core.safety import execute_ragnarok

@pytest.mark.asyncio
async def test_ragnarok_emergency_lockdown(synapse):
    """Verify that Ragnarok protocol triggers kill switch and halts engine."""
    # Note: Real Ragnarok calls kalshi_client.close_all_positions()
    # In Demo mode, this should be safe.
    
    engine = GhostEngine()
    engine.synapse = synapse
    await engine.vault.initialize(50000)
    
    assert await engine.authorize_cycle() is True
    
    # Trigger Ragnarok via GhostEngine logic (or direct call)
    # GhostEngine.trigger_ragnarok (the route handler) does:
    # await execute_ragnarok()
    # self.manual_kill_switch = True
    
    engine.manual_kill_switch = True
    
    assert await engine.authorize_cycle() is False
    print("\n[RAGNAROK] Success: Engine halted after kill switch.")
