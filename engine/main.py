"""
GHOST ENGINE v3.0 - 4 MEGA-AGENT ARCHITECTURE
Codename: Sentient Alpha (Consolidated)

The 4 Pillars of Profit:
1. SOUL - System, Memory & Evolution
2. SENSES - Surveillance & Signal Detection
3. BRAIN - Intelligence & Mathematical Verification
4. HAND - Precision Strike & Budget Sentinel
"""

import asyncio
import os
import signal
import sys
import json
from datetime import datetime
from typing import List, Optional

from aiohttp import web
from colorama import init, Fore, Style
from dotenv import load_dotenv

from core.bus import EventBus
from core.vault import RecursiveVault
from core.network import kalshi_client

# Import 4 Mega-Agents
from agents.soul import SoulAgent
from agents.senses import SensesAgent
from agents.brain import BrainAgent
from agents.hand import HandAgent
from agents.gateway import GatewayAgent
from agents.base import BaseAgent

# Initialize Colorama and Env
init()
load_dotenv()


class GhostEngine:
    """
    The Ghost Orchestrator v3.0 (4 Mega-Agent Architecture)
    Codename: Sentient Alpha
    """
    
    def __init__(self):
        self.bus: EventBus = EventBus()
        self.vault: RecursiveVault = RecursiveVault()
        self.running: bool = True
        self.agents: List[BaseAgent] = []
        self.cycle_count: int = 0
        self.is_processing: bool = False
        self.manual_kill_switch: bool = False
        self.sse_clients: List[asyncio.Queue] = []

        # Double-Entry Queues
        self.opp_queue: asyncio.Queue = asyncio.Queue()
        self.exec_queue: asyncio.Queue = asyncio.Queue()

    async def run_soul(self):
        """SOUL: Pre-flight and oversight."""
        while self.running:
            if not self.manual_kill_switch:
                message = {"cycle_id": 1, "paper_trading": True}
                await self.soul.on_cycle_start(message)
            await asyncio.sleep(60)  # Check every minute

    async def run_senses(self):
        """SENSES: Continuous scanning and queueing opportunities."""
        while self.running:
            if not self.manual_kill_switch:
                await self.senses.run_scout(self.opp_queue)
            await asyncio.sleep(10)  # Scan every 10 seconds

    async def run_brain(self):
        """BRAIN: Process opportunities into executions."""
        while self.running:
            if not self.manual_kill_switch:
                await self.brain.run_intelligence(self.opp_queue, self.exec_queue)
            await asyncio.sleep(1)  # Check queue frequently

    async def run_hand(self):
        """HAND: Execute trades from queue."""
        while self.running:
            if not self.manual_kill_switch:
                await self.hand.run_execution(self.exec_queue)
            await asyncio.sleep(1)  # Check queue frequently

    async def keep_alive(self):
        """Keep the event loop alive."""
        while self.running:
            await asyncio.sleep(1)
        
        # Mega-Agent references for inter-agent communication
        self.soul: Optional[SoulAgent] = None
        self.senses: Optional[SensesAgent] = None
        self.brain: Optional[BrainAgent] = None
        self.hand: Optional[HandAgent] = None

    async def initialize_system(self):
        print(f"{Fore.MAGENTA}=========================================={Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}   GHOST ENGINE v3.0 (4 MEGA-AGENTS)     {Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}=========================================={Style.RESET_ALL}")
        
        # Subscribe to System Logs
        await self.bus.subscribe("SYSTEM_LOG", self.handle_log)
        
        # Initialize 4 Mega-Agents
        print(f"{Fore.CYAN}[GHOST] Initializing 4 Mega-Agent Pillars...{Style.RESET_ALL}")
        
        try:
            # 1. SOUL - Executive Director
            self.soul = SoulAgent(1, self.bus, vault=self.vault)
            await self.soul.start()
            self.agents.append(self.soul)
            
            # 2. SENSES - Surveillance
            self.senses = SensesAgent(2, self.bus, kalshi_client=kalshi_client)
            await self.senses.start()
            self.agents.append(self.senses)
            
            # 3. BRAIN - Intelligence (needs reference to Senses for opportunity queue)
            self.brain = BrainAgent(3, self.bus, senses_agent=self.senses)
            await self.brain.start()
            self.agents.append(self.brain)
            
            # 4. HAND - Execution (needs reference to Brain and Vault)
            self.hand = HandAgent(4, self.bus, vault=self.vault, brain_agent=self.brain, kalshi_client=kalshi_client)
            await self.hand.start()
            self.agents.append(self.hand)
            
            # Gateway for SSE streaming (kept for backend communication)
            gateway = GatewayAgent(5, self.bus, vault=self.vault)
            await gateway.start()
            self.agents.append(gateway)
            
        except Exception as e:
            print(f"{Fore.RED}[GHOST] Failed to initialize agents: {e}{Style.RESET_ALL}")
        
        # Initialize Vault
        await self.vault.initialize(30000)  # $300.00
        
        print(f"{Fore.GREEN}[GHOST] SYSTEM ONLINE - 4 Pillars Active.{Style.RESET_ALL}")

    async def handle_log(self, message):
        """Central logging handler."""
        pass

    def authorize_cycle(self) -> bool:
        """
        SOUL: Strategic Authorization
        Checks Kill Switch and safety conditions.
        """
        # Temporarily disabled for manual testing
        # if self.manual_kill_switch:
        #     print(f"{Fore.RED}[GHOST] 💀 MANUAL KILL SWITCH ACTIVE. HALTING.{Style.RESET_ALL}")
        #     return False

        if os.getenv("KILL_SWITCH") == "true":
            print(f"{Fore.RED}[GHOST] ENV KILL SWITCH ACTIVE. HALTING.{Style.RESET_ALL}")
            return False

        if self.vault.kill_switch_active:
            print(f"{Fore.RED}[GHOST] VAULT KILL SWITCH ACTIVE. HALTING.{Style.RESET_ALL}")
            return False

        # Hard floor check ($255)
        if self.vault.current_balance < 25500:
            print(f"{Fore.RED}[GHOST] HARD FLOOR BREACH ($255). EMERGENCY LOCKDOWN.{Style.RESET_ALL}")
            return False

        # Maintenance window
        now = datetime.now()
        if now.hour == 23 and now.minute >= 55:
            print(f"{Fore.YELLOW}[GHOST] MAINTENANCE WINDOW. STANDING DOWN.{Style.RESET_ALL}")
            return False

        return True

    async def execute_single_cycle(self, is_paper_trading: bool = True):
        """Execute a single trading cycle with 4 Mega-Agents."""
        if self.is_processing:
            print(f"{Fore.YELLOW}[GHOST] Cycle already in progress. Ignoring.{Style.RESET_ALL}")
            return
        
        self.is_processing = True
        self.cycle_count += 1
        
        try:
            # SOUL: Authorization Check
            if not self.authorize_cycle():
                msg = f"Cycle {self.cycle_count} not authorized."
                print(f"{Fore.YELLOW}[GHOST] {msg}{Style.RESET_ALL}")
                await self.bus.publish("SYSTEM_LOG", {
                    "level": "WARN",
                    "message": msg,
                    "agent_id": 1,
                    "timestamp": datetime.now().isoformat()
                }, "GHOST")
                return
            
            # Cycle Start
            await self.bus.publish("SYSTEM_LOG", {
                "level": "INFO", 
                "message": f"[GHOST] CYCLE #{self.cycle_count} START - 4 Pillars Activated",
                "agent_id": 1,
                "timestamp": datetime.now().isoformat()
            }, "GHOST")

            # Trigger CYCLE_START for SOUL
            await self.bus.publish("CYCLE_START", {
                "cycle": self.cycle_count, 
                "isPaperTrading": is_paper_trading
            }, "GHOST")
            
            # Allow agents to process
            await asyncio.sleep(0.5)
            
            # Broadcast TICK for periodic updates
            await self.bus.publish("TICK", {
                "cycle": self.cycle_count, 
                "isPaperTrading": is_paper_trading
            }, "GHOST")
            
            # Cycle Complete
            await self.bus.publish("SYSTEM_LOG", {
                "level": "SUCCESS",
                "message": f"✓ CYCLE #{self.cycle_count} COMPLETE",
                "agent_id": 1,
                "timestamp": datetime.now().isoformat()
            }, "GHOST")

            print(f"{Fore.GREEN}[GHOST] Cycle {self.cycle_count} complete.{Style.RESET_ALL}")
        
        except Exception as e:
            print(f"{Fore.RED}[GHOST] Cycle {self.cycle_count} failed: {e}{Style.RESET_ALL}")
        
        finally:
            self.is_processing = False

    async def shutdown(self):
        print(f"\n{Fore.RED}[GHOST] SHUTDOWN PROTOCOL INITIATED.{Style.RESET_ALL}")
        self.running = False
        await kalshi_client.close()
        print(f"{Fore.RED}[GHOST] ALL SYSTEMS OFFLINE.{Style.RESET_ALL}")

    async def start_http_server(self):
        """HTTP server for triggering cycles and SSE streaming."""
        app = web.Application()
        
        async def trigger_cycle(request):
            data = await request.json()
            is_paper = data.get('isPaperTrading', True)
            asyncio.create_task(self.execute_single_cycle(is_paper))
            return web.json_response({
                "status": "triggered",
                "cycleId": self.cycle_count + 1,
                "isProcessing": self.is_processing
            })
        
        async def activate_kill_switch(request):
            self.manual_kill_switch = True
            await self.bus.publish("SYSTEM_LOG", {
                "level": "ERROR", 
                "message": "[GHOST] 💀 MANUAL KILL SWITCH ACTIVATED",
                "agent_id": 1,
                "timestamp": datetime.now().isoformat()
            }, "GHOST")
            return web.json_response({
                "status": "killed",
                "message": "Manual Kill Switch Activated."
            })
        
        async def reset_system(request):
            self.manual_kill_switch = False
            self.is_processing = False
            return web.json_response({"status": "reset"})
        
        async def health_check(request):
            return web.json_response({
                "status": "healthy",
                "agents": 4,
                "cycle": self.cycle_count,
                "balance": self.vault.current_balance / 100
            })
        
        async def stream_logs(request):
            response = web.StreamResponse(
                status=200,
                reason='OK',
                headers={
                    'Content-Type': 'text/event-stream',
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'Access-Control-Allow-Origin': '*'
                }
            )
            await response.prepare(request)
            
            queue = asyncio.Queue()
            self.sse_clients.append(queue)
            
            try:
                while True:
                    event = await queue.get()
                    data = json.dumps(event)
                    await response.write(f"data: {data}\n\n".encode())
            except asyncio.CancelledError:
                pass
            finally:
                self.sse_clients.remove(queue)
            
            return response
        
        app.router.add_post('/trigger', trigger_cycle)
        app.router.add_post('/kill-switch', activate_kill_switch)
        app.router.add_post('/reset', reset_system)
        app.router.add_get('/health', health_check)
        app.router.add_get('/stream', stream_logs)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 3002)
        await site.start()
        
        print(f"{Fore.CYAN}[GHOST] HTTP Server online at http://0.0.0.0:3002{Style.RESET_ALL}")
        
        # Subscribe to bus events for SSE broadcast
        await self.bus.subscribe("SYSTEM_LOG", self._broadcast_to_sse)
        await self.bus.subscribe("VAULT_UPDATE", self._broadcast_to_sse)
        await self.bus.subscribe("SIM_RESULT", self._broadcast_to_sse)
        await self.bus.subscribe("SYSTEM_STATE", self._broadcast_to_sse)
        
    async def _broadcast_to_sse(self, message):
        """Broadcast bus events to all SSE clients."""
        event_type = message.topic
        payload = message.payload

        formatted_event = None

        # 4-Agent Phase Mapping
        AGENT_TO_PHASE = {
            1: 1,  # SOUL
            2: 2,  # SENSES
            3: 3,  # BRAIN
            4: 4,  # HAND
            5: 4,  # Gateway (part of Hand output)
        }
        
        if event_type == "SYSTEM_LOG":
            agent_id = payload.get("agent_id", 1)
            phase_id = AGENT_TO_PHASE.get(agent_id, 1)
            
            formatted_event = {
                "type": "LOG",
                "log": {
                    "id": f"log-{datetime.now().timestamp()}",
                    "timestamp": payload.get("timestamp", datetime.now().isoformat()),
                    "agentId": agent_id,
                    "cycleId": self.cycle_count,
                    "phaseId": phase_id,
                    "message": payload.get("message", ""),
                    "level": payload.get("level", "INFO")
                }
            }
        elif event_type == "VAULT_UPDATE":
            formatted_event = {"type": "VAULT", "state": payload}
        elif event_type == "SIM_RESULT":
            formatted_event = {"type": "SIMULATION", "state": payload}
        elif event_type == "SYSTEM_STATE":
            formatted_event = {"type": "STATE", "state": payload}
            
        if formatted_event:
            for queue in self.sse_clients:
                try:
                    await queue.put(formatted_event)
                except:
                    pass
        
    async def run(self):
        """Main event loop with continuous queue processing."""
        await self.initialize_system()
        await self.start_http_server()

        # Continuous agent operations with queues
        await asyncio.gather(
            self.run_soul(),
            self.run_senses(),
            self.run_brain(),
            self.run_hand(),
            self.keep_alive()
        )
        
    def start(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.shutdown()))

        try:
            loop.run_until_complete(self.run())
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
        finally:
            loop.run_until_complete(self.shutdown())
            loop.close()


if __name__ == "__main__":
    engine = GhostEngine()
    engine.start()
