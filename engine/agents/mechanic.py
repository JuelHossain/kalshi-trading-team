import asyncio
import time
import os
import psutil
from agents.base import BaseAgent
from core.bus import EventBus
from colorama import Fore, Style

class MechanicAgent(BaseAgent):
    """
    Agent 11: The Mechanic
    Role: System Diagnostics & Health Monitoring.
    Checks latency, memory usage, and process health.
    """
    
    def __init__(self, agent_id: int, bus: EventBus):
        super().__init__("MECHANIC", agent_id, bus)
        self.start_time = time.time()

    async def start(self):
        await self.log("System Diagnostics Online. Monitoring local resources...")
        await self.bus.subscribe("TICK", self.handle_health_check)

    async def handle_health_check(self, message):
        cycle = message.payload.get('cycle', 0)
        
        # Run diagnostics every 60 cycles (approx 1 minute)
        if cycle % 60 == 0:
            stats = self.get_system_stats()
            await self.log(f"HEALTH: CPU {stats['cpu']}% | MEM {stats['mem']}% | Latency {stats['latency']}ms")
            
            # Publish Health Report
            await self.bus.publish("SYSTEM_HEALTH", stats, self.name)
            
            # Simple threshold warning
            if stats['cpu'] > 80:
                await self.log(f"{Fore.RED}WARNING: CPU Load High!{Style.RESET_ALL}")

    def get_system_stats(self) -> dict:
        uptime = time.time() - self.start_time
        # In a real environment, we'd ping the Kalshi API for true latency
        latency = 42 # Mock latency
        
        return {
            "status": "OPTIMAL",
            "cpu": psutil.cpu_percent(),
            "mem": psutil.virtual_memory().percent,
            "latency": latency,
            "uptime_seconds": int(uptime)
        }
