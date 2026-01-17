import asyncio
import os
import signal
from agents.base import BaseAgent
from core.bus import EventBus
from colorama import Fore, Style

class RagnarokAgent(BaseAgent):
    """
    Agent 12: Ragnarok
    Role: The Global Kill Switch.
    Triggers on catastrophic failures or manual override.
    """
    
    def __init__(self, agent_id: int, bus: EventBus):
        super().__init__("RAGNAROK", agent_id, bus)

    async def start(self):
        await self.log("Ragnarok Protocol Armed. Monitoring for Kill Signals.")
        await self.bus.subscribe("EMERGENCY_KILL", self.initiate_ragnarok)

    async def initiate_ragnarok(self, message):
        reason = message.payload.get('reason', 'External Intervention')
        await self.log(f"{Fore.RED}!!! RAGNAROK INITIATED: {reason} !!!{Style.RESET_ALL}")
        
        # 1. Broadast KILL to all agents
        await self.bus.publish("KILL_SIGNAL", {"reason": reason}, self.name)
        
        # 2. Simulated: Cancel All Orders (V2 Kalshi)
        await self.log("Cancelling all standing orders on Kalshi (Simulated)...")
        
        # 3. Shutdown the core engine
        await self.log("Shutting down core engine in 3 seconds...")
        await asyncio.sleep(3)
        
        # This will exit the main loop if we handle KILL_SIGNAL in main.py
        # Or we can just kill the process
        print(f"{Fore.RED}RAGNAROK COMPLETE. SYSTEM OFFLINE.{Style.RESET_ALL}")
        os.kill(os.getpid(), signal.SIGINT)
