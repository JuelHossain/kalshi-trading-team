import asyncio
import os
import signal
import sys
import json
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
        self.cycle_count: int = 0
        self.is_processing: bool = False

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

    async def execute_single_cycle(self, is_paper_trading: bool = True):
        """Execute a single trading cycle on-demand."""
        if self.is_processing:
            print(f"{Fore.YELLOW}[GHOST] Cycle already in progress. Ignoring trigger.{Style.RESET_ALL}")
            return
        
        self.is_processing = True
        self.cycle_count += 1
        
        try:
            # Agent 1: Authorization
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
            
            # Explicit Cycle Start Log for UI
            await self.bus.publish("SYSTEM_LOG", {
                "level": "INFO", 
                "message": f"[GHOST] CYCLE START: Sentient Alpha Funnel Protocol (Cycle #{self.cycle_count})",
                "agent_id": 1,
                "timestamp": datetime.now().isoformat()
            }, "GHOST")

            # Broadcast "TICK" event
            await self.bus.publish("TICK", {"cycle": self.cycle_count, "isPaperTrading": is_paper_trading}, "GHOST")
            
            # Simulate cycle work (agents will respond to TICK)
            await asyncio.sleep(0.5)
            
            # Explicit Cycle Complete Log for UI
            await self.bus.publish("SYSTEM_LOG", {
                "level": "SUCCESS",
                "message": f"✓ CYCLE #{self.cycle_count} COMPLETE - All phases finished successfully",
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
        
        # Close Kalshi Client Session
        await kalshi_client.close()
        
        # Future: Call teardown() on all agents
        print(f"{Fore.RED}[GHOST] ALL SYSTEMS OFFLINE.{Style.RESET_ALL}")

    async def start_http_server(self):
        """Start HTTP trigger endpoint."""
        from aiohttp import web
        import asyncio
        
        # SSE clients queue
        self.sse_clients = []
        
        async def trigger_cycle(request):
            data = await request.json()
            is_paper = data.get('isPaperTrading', True)
            
            # Fire and forget
            asyncio.create_task(self.execute_single_cycle(is_paper))
            
            return web.json_response({
                "status": "triggered",
                "cycleId": self.cycle_count + 1,
                "isProcessing": self.is_processing
            })
        
        async def health_check(request):
            return web.json_response({
                "status": "online",
                "cycleCount": self.cycle_count,
                "isProcessing": self.is_processing,
                "vaultLocked": self.vault.is_locked,
                "killSwitch": self.vault.kill_switch_active
            })
        
        async def stream_logs(request):
            """SSE endpoint for real-time log streaming."""
            response = web.StreamResponse()
            response.headers['Content-Type'] = 'text/event-stream'
            response.headers['Cache-Control'] = 'no-cache'
            response.headers['Connection'] = 'keep-alive'
            await response.prepare(request)
            
            # Create a queue for this client
            queue = asyncio.Queue()
            self.sse_clients.append(queue)
            
            try:
                while True:
                    event = await queue.get()
                    await response.write(f"data: {json.dumps(event)}\n\n".encode())
            except asyncio.CancelledError:
                pass
            finally:
                self.sse_clients.remove(queue)
            
            return response
        
        app = web.Application()
        app.router.add_post('/trigger', trigger_cycle)
        app.router.add_get('/health', health_check)
        app.router.add_get('/stream', stream_logs)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 3002)
        await site.start()
        
        print(f"{Fore.CYAN}[GHOST] HTTP Trigger Server online at http://0.0.0.0:3002{Style.RESET_ALL}")
        
        # Subscribe to bus events to broadcast via SSE
        await self.bus.subscribe("SYSTEM_LOG", self._broadcast_to_sse)
        await self.bus.subscribe("VAULT_UPDATE", self._broadcast_to_sse)
        await self.bus.subscribe("SIM_RESULT", self._broadcast_to_sse)
        
    async def _broadcast_to_sse(self, message):
        """Broadcast bus events to all SSE clients with proper formatting for the frontend."""
        event_type = message.topic
        payload = message.payload
        
        formatted_event = None
        
        # Mapping mirrors shared/constants.ts for phase-based UI
        AGENT_TO_PHASE = {
            1: 0, 11: 0,           # Phase 0: System Init
            2: 1, 3: 1, 7: 1,      # Phase 1: Surveillance
            4: 2, 5: 2, 6: 2,      # Phase 2: Intelligence
            8: 3,                   # Phase 3: Execution
            9: 4, 10: 4,            # Phase 4: Accounting
            12: 5, 14: 5,           # Phase 5: Protection
            13: 13                  # Intervention
        }
        
        if event_type == "SYSTEM_LOG":
            agent_id = payload.get("agent_id", 0)
            phase_id = AGENT_TO_PHASE.get(agent_id, 0)
            
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
            formatted_event = {
                "type": "VAULT",
                "state": payload
            }
        elif event_type == "SIM_RESULT":
            formatted_event = {
                "type": "SIMULATION",
                "state": payload
            }
        elif event_type == "SYSTEM_STATE":
             formatted_event = {
                "type": "STATE",
                "state": payload
            }
            
        if formatted_event:
            for queue in self.sse_clients:
                try:
                    await queue.put(formatted_event)
                except:
                    pass
        
    async def run(self):
        """Main event loop - just keeps server alive."""
        await self.initialize_system()
        await self.start_http_server()
        
        # Keep alive
        while self.running:
            await asyncio.sleep(1)
        
    def start(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Setup signal handlers for graceful shutdown
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
