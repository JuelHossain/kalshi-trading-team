import asyncio
import os
import signal
import sys
from datetime import datetime
from typing import List, Optional

from colorama import init, Fore, Style
from dotenv import load_dotenv

from core.bus import EventBus
from core.vault import RecursiveVault
from core.network import kalshi_client

# Import Agents (Moved to top for clarity and Type Hinting)
from agents.scout import ScoutAgent
from agents.interceptor import InterceptorAgent
from agents.analyst import AnalystAgent
from agents.sim_scientist import SimScientistAgent
from agents.auditor import AuditorAgent
from agents.sniper import SniperAgent
from agents.executioner import ExecutionerAgent
from agents.accountant import AccountantAgent
from agents.historian import HistorianAgent
from agents.mechanic import MechanicAgent
from agents.ragnarok import RagnarokAgent
from agents.fixer import FixerAgent
from agents.gateway import GatewayAgent
from agents.base import BaseAgent

# Initialize Colorama and Env
init()
load_dotenv()

class GhostEngine:
    """
    The Ghost Orchestrator (Python 3.12 Engine)
    Codename: Sentient Alpha
    """
    
    def __init__(self):
        self.bus: EventBus = EventBus()
        self.vault: RecursiveVault = RecursiveVault()
        self.running: bool = True
        self.agents: List[BaseAgent] = []

    async def initialize_system(self):
        print(f"{Fore.MAGENTA}=========================================={Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}   GHOST ORCHESTRATOR v2.0 (PYTHON IO)    {Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}=========================================={Style.RESET_ALL}")
        
        # Subscribe to System Logs
        await self.bus.subscribe("SYSTEM_LOG", self.handle_log)
        
        # Initialize Agents
        print(f"{Fore.CYAN}[GHOST] Initializing 12-Agent Mesh...{Style.RESET_ALL}")
        
        # Mapping for easier initialization
        agent_classes = [
            (ScoutAgent, 2),
            (InterceptorAgent, 3),
            (AnalystAgent, 4),
            (SimScientistAgent, 5),
            (AuditorAgent, 6),
            (SniperAgent, 7),
            (ExecutionerAgent, 8),
            (AccountantAgent, 9),
            (HistorianAgent, 10),
            (MechanicAgent, 11),
            (RagnarokAgent, 12),
            (FixerAgent, 13),
            (GatewayAgent, 14)
        ]
        for cls, agent_id in agent_classes:

            try:
                # Accountant and Gateway need the vault reference
                if cls in [AccountantAgent, GatewayAgent]:
                    agent = cls(agent_id, self.bus, vault=self.vault)
                else:
                    agent = cls(agent_id, self.bus)
                
                await agent.start()
                self.agents.append(agent)
            except Exception as e:
                print(f"{Fore.RED}[GHOST] Failed to start Agent {agent_id} ({cls.__name__}): {e}{Style.RESET_ALL}")
        
        # Initialize Vault with Mock Balances (or Real if API connected)
        await self.vault.initialize(30000) # $300.00
        
        print(f"{Fore.GREEN}[GHOST] SYSTEM ONLINE.{Style.RESET_ALL}")

    async def handle_log(self, message):
        """Central logging handler."""
        # Future: Stream to Supabase or specialized logging agent
        pass

    def authorize_cycle(self) -> bool:
        """
        Agent 1: Strategic Authorization
        Checks Kill Switch and Maintenance Windows.
        """
        # 1. Kill Switch
        if os.getenv("KILL_SWITCH") == "true":
            print(f"{Fore.RED}[GHOST] ENV KILL SWITCH ACTIVE. HALTING.{Style.RESET_ALL}")
            return False

        # 2. Vault Kill Switch (85% Protocol)
        if self.vault.kill_switch_active:
            print(f"{Fore.RED}[GHOST] VAULT KILL SWITCH ACTIVE. HALTING.{Style.RESET_ALL}")
            return False

        # 3. Maintenance Window (Mock 23:55)

        now = datetime.now()
        if now.hour == 23 and now.minute >= 55:
            print(f"{Fore.YELLOW}[GHOST] MAINTENANCE WINDOW. STANDING DOWN.{Style.RESET_ALL}")
            return False

        return True

    async def run_cycle(self):
        """Main Heartbeat Loop."""
        cycle_count = 0
        while self.running:
            cycle_count += 1
            
            # Agent 1: Authorization
            if not self.authorize_cycle():
                await asyncio.sleep(60) # Back off if not authorized
                continue

            # Broadcast "TICK" event
            await self.bus.publish("TICK", {"cycle": cycle_count}, "GHOST")
            
            await asyncio.sleep(1)

    async def shutdown(self):
        print(f"\n{Fore.RED}[GHOST] SHUTDOWN PROTOCOL INITIATED.{Style.RESET_ALL}")
        self.running = False
        
        # Close Kalshi Client Session
        await kalshi_client.close()
        
        # Future: Call teardown() on all agents
        print(f"{Fore.RED}[GHOST] ALL SYSTEMS OFFLINE.{Style.RESET_ALL}")
        
    def start(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Setup signal handlers for graceful shutdown
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.shutdown()))

        try:
            loop.run_until_complete(self.initialize_system())
            loop.run_until_complete(self.run_cycle())
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
        finally:
            loop.close()

if __name__ == "__main__":
    engine = GhostEngine()
    engine.start()
