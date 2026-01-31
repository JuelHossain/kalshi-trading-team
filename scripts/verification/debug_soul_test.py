import asyncio
import os
from dotenv import load_dotenv

# Path to .env
env_path = os.path.join(os.getcwd(), "engine", ".env")
load_dotenv(env_path)

from engine.core.bus import EventBus
from engine.core.synapse import Synapse
from engine.core.vault import RecursiveVault
from engine.agents.soul import SoulAgent

async def debug_soul():
    print("Testing SoulAgent...")
    bus = EventBus()
    synapse = Synapse(db_path="debug_ghost.db")
    vault = RecursiveVault()
    await vault.initialize(50000)
    
    soul = SoulAgent(1, bus, vault=vault, synapse=synapse)
    print("Initializing...")
    await soul.start()
    
    print("Sending START_AUTOPILOT...")
    await bus.publish("SYSTEM_CONTROL", {"action": "START_AUTOPILOT", "isPaperTrading": True}, "DEBUG")
    
    # Give it a tiny bit of time
    await asyncio.sleep(0.5)
    
    print(f"Autopilot Enabled: {soul.autopilot_enabled}")
    assert soul.autopilot_enabled is True
    
    print("Sending STOP_AUTOPILOT...")
    await bus.publish("SYSTEM_CONTROL", {"action": "STOP_AUTOPILOT"}, "DEBUG")
    await asyncio.sleep(0.5)
    
    print(f"Autopilot Enabled: {soul.autopilot_enabled}")
    assert soul.autopilot_enabled is False
    
    await soul.stop()
    print("Soul test complete!")

if __name__ == "__main__":
    try:
        asyncio.run(debug_soul())
    except Exception as e:
        import traceback
        traceback.print_exc()
