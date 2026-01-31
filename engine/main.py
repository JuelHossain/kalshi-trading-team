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
import json
import os
import signal
import uuid
from datetime import datetime

from aiohttp import web
from colorama import Fore, Style, init
from dotenv import load_dotenv

# Load Env BEFORE imports
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from agents.base import BaseAgent
from agents.brain import BrainAgent
from agents.gateway import GatewayAgent
from agents.hand import HandAgent
from agents.senses import SensesAgent

# Import 4 Mega-Agents
from agents.soul import SoulAgent
from core.auth import auth_manager
from core.bus import EventBus
from core.network import kalshi_client
from core.safety import execute_ragnarok
from core.synapse import Synapse
from core.vault import RecursiveVault

# Initialize Colorama
init()


class GhostEngine:
    """
    The Ghost Orchestrator v3.0 (4 Mega-Agent Architecture)
    Codename: Sentient Alpha
    """

    def __init__(self):
        self.bus: EventBus = EventBus()
        self.synapse: Synapse = Synapse()
        self.vault: RecursiveVault = RecursiveVault()
        self.running: bool = True
        self.agents: list[BaseAgent] = []
        self.cycle_count: int = 0
        self.is_processing: bool = False
        self.last_cycle_time: datetime = None  # Rate limit tracking
        self.manual_kill_switch: bool = False
        self.sse_clients: set[asyncio.Queue] = set()

        # Double-Entry Queues
        self.opp_queue: asyncio.Queue = asyncio.Queue()
        self.exec_queue: asyncio.Queue = asyncio.Queue()



    async def initialize_system(self):
        print(f"{Fore.MAGENTA}=========================================={Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}   GHOST ENGINE v3.0 (4 MEGA-AGENTS)     {Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}=========================================={Style.RESET_ALL}")

        # Subscribe to System Logs (Managed by SSE broadcast)
        # await self.bus.subscribe("SYSTEM_LOG", self.handle_log)

        # Autopilot / Request Cycle Support
        # Autopilot / Request Cycle Support
        await self.bus.subscribe("REQUEST_CYCLE", self._handle_cycle_request)
        
        # Fail-Fast Protocol
        await self.bus.subscribe("SYSTEM_FATAL", self._handle_system_fatal)

        # Initialize 4 Mega-Agents
        print(f"{Fore.CYAN}[GHOST] Initializing 4 Mega-Agent Pillars...{Style.RESET_ALL}")

        try:
            # 1. SOUL - Executive Director
            self.soul = SoulAgent(1, self.bus, vault=self.vault, synapse=self.synapse)
            await self.soul.start()
            self.agents.append(self.soul)

            # 2. SENSES - Surveillance
            # 2. SENSES - Surveillance
            self.senses = SensesAgent(2, self.bus, kalshi_client=kalshi_client, synapse=self.synapse)
            await self.senses.start()
            self.agents.append(self.senses)

            # 3. BRAIN - Intelligence (needs reference to Senses for opportunity queue)
            # 3. BRAIN - Intelligence (Strict Decoupling via Synapse)
            self.brain = BrainAgent(3, self.bus, synapse=self.synapse)
            await self.brain.start()
            self.agents.append(self.brain)

            # 4. HAND - Execution (Strict Decoupling via Synapse)
            self.hand = HandAgent(
                4, self.bus, vault=self.vault, kalshi_client=kalshi_client, synapse=self.synapse
            )
            await self.hand.start()
            self.agents.append(self.hand)

            # Gateway for SSE streaming (kept for backend communication)
            gateway = GatewayAgent(5, self.bus, vault=self.vault)
            await gateway.start()
            self.agents.append(gateway)

        except Exception as e:
            print(f"{Fore.RED}[GHOST] Failed to initialize agents: {e}{Style.RESET_ALL}")

        # Initialize Vault with Real Balance
        try:
            real_balance = await kalshi_client.get_balance()
            print(f"{Fore.GREEN}[SOUL] Fetched Real Balance: ${real_balance/100:.2f}{Style.RESET_ALL}")
            await self.vault.initialize(real_balance)
        except Exception as e:
            print(f"{Fore.RED}[SOUL] Failed to fetch balance: {e}. Defaulting to $0 (Safety Mode).{Style.RESET_ALL}")
            await self.vault.initialize(0)

        print(f"{Fore.GREEN}[GHOST] SYSTEM ONLINE - 4 Pillars Active.{Style.RESET_ALL}")



    async def authorize_cycle(self) -> bool:
        """
        SOUL: Strategic Authorization
        Checks Kill Switch and safety conditions.
        """
        # Temporarily disabled for manual testing
        if self.last_cycle_time:
            elapsed = (datetime.now() - self.last_cycle_time).total_seconds()
            if elapsed < 30:
                print(f"{Fore.YELLOW}[GHOST] Rate limit: Wait {30 - elapsed:.0f}s before next cycle.{Style.RESET_ALL}")
                return False

        if self.manual_kill_switch:
            print(f"{Fore.RED}[GHOST] 💀 MANUAL KILL SWITCH ACTIVE. HALTING.{Style.RESET_ALL}")
            return False

        if os.getenv("KILL_SWITCH") == "true":
            print(f"{Fore.RED}[GHOST] ENV KILL SWITCH ACTIVE. HALTING.{Style.RESET_ALL}")
            return False

        if self.vault.kill_switch_active:
            print(f"{Fore.RED}[GHOST] VAULT KILL SWITCH ACTIVE. HALTING.{Style.RESET_ALL}")
            return False

        # Soul Lockdown Check (API Failure / Hard Floor)
        if hasattr(self, "soul") and self.soul.is_locked_down:
            print(f"{Fore.RED}[GHOST] SOUL LOCKDOWN ACTIVE. HALTING.{Style.RESET_ALL}")
            return False

        # Synapse Error Box Check (Strict Decoupling)
        if hasattr(self, "synapse") and self.synapse:
            error_count = await self.synapse.errors.size()
            if error_count > 0:
                print(f"{Fore.RED}[GHOST] 🚨 ERROR BOX ACTIVE ({error_count} errors). HALTING.{Style.RESET_ALL}")
                # Optional: log a system message
                return False

        # 1. Hard floor check ($255) - ATOMIC with vault update
        try:
            real_balance = await kalshi_client.get_balance()

            # UPDATE VAULT FIRST, then check - ensures atomic read-check
            self.vault.current_balance = real_balance

            if real_balance < self.vault.HARD_FLOOR_CENTS:
                print(f"{Fore.RED}[GHOST] 🚨 HARD FLOOR BREACH (${real_balance/100:.2f} < ${self.vault.HARD_FLOOR_CENTS/100:.2f}). EMERGENCY LOCKDOWN.{Style.RESET_ALL}")
                return False
        except Exception:
            # Fallback to vault cache if API fails
            if self.vault.current_balance < self.vault.HARD_FLOOR_CENTS:
                return False

        # Maintenance window
        # now = datetime.now()
        # if now.hour == 23 and now.minute >= 55:
        #     print(f"{Fore.YELLOW}[GHOST] MAINTENANCE WINDOW. STANDING DOWN.{Style.RESET_ALL}")
        #     return False

        self.last_cycle_time = datetime.now()
        return True

    async def execute_single_cycle(self, is_paper_trading: bool = True):
        """Execute a single trading cycle with 4 Mega-Agents."""
        if self.is_processing:
            print(f"{Fore.YELLOW}[GHOST] Cycle already in progress. Ignoring.{Style.RESET_ALL}")
            return

        self.is_processing = True
        try:
            # SOUL: Authorization Check
            if not await self.authorize_cycle():
                msg = f"Cycle {self.cycle_count + 1} not authorized."
                print(f"{Fore.YELLOW}[GHOST] {msg}{Style.RESET_ALL}")
                await self.bus.publish(
                    "SYSTEM_LOG",
                    {
                        "level": "WARN",
                        "message": msg,
                        "agent_id": 1,
                        "timestamp": datetime.now().isoformat(),
                    },
                    "GHOST",
                )
                return

            self.cycle_count += 1

            # Cycle Start
            await self.bus.publish(
                "SYSTEM_LOG",
                {
                    "level": "INFO",
                    "message": f"[GHOST] CYCLE #{self.cycle_count} START - 4 Pillars Activated",
                    "agent_id": 1,
                    "timestamp": datetime.now().isoformat(),
                },
                "GHOST",
            )

            # Trigger CYCLE_START for SOUL
            await self.bus.publish(
                "CYCLE_START",
                {"cycle": self.cycle_count, "isPaperTrading": is_paper_trading},
                "GHOST",
            )

            # Allow agents to process
            await asyncio.sleep(0.5)

            # Broadcast TICK for periodic updates
            await self.bus.publish(
                "TICK", {"cycle": self.cycle_count, "isPaperTrading": is_paper_trading}, "GHOST"
            )

            # Cycle Complete
            await self.bus.publish(
                "SYSTEM_LOG",
                {
                    "level": "SUCCESS",
                    "message": f"✓ CYCLE #{self.cycle_count} COMPLETE",
                    "agent_id": 1,
                    "timestamp": datetime.now().isoformat(),
                },
                "GHOST",
            )

            print(f"{Fore.GREEN}[GHOST] Cycle {self.cycle_count} complete.{Style.RESET_ALL}")

        except Exception as e:
            print(f"{Fore.RED}[GHOST] Cycle {self.cycle_count} failed: {e}{Style.RESET_ALL}")

        finally:
            self.is_processing = False
            await self.bus.publish(
                "SYSTEM_STATE",
                {"isProcessing": False, "activeAgentId": None},
                "GHOST",
            )
            # Notify Soul that cycle is finished
            await self.bus.publish("CYCLE_COMPLETE", {"cycle": self.cycle_count}, "GHOST")

    async def _handle_cycle_request(self, message):
        """Handle incoming request to start a new cycle"""
        if not self.is_processing and self.running:
             # Default to live trading unless specified
             is_paper = message.payload.get("isPaperTrading", True)
             # Use ensure_future or call directly (it's already guarded by is_processing)
             asyncio.create_task(self.execute_single_cycle(is_paper_trading=is_paper))

    async def _handle_system_fatal(self, message):
        """Handle fatal errors by shutting down the entire engine immediately."""
        error_msg = message.payload.get("message", "Unknown Fatal Error")
        agent_id = message.sender
        
        print(f"\n{Fore.RED}[GHOST] 💀 FATAL ERROR reported by {agent_id}: {error_msg}{Style.RESET_ALL}")
        print(f"{Fore.RED}[GHOST] INITIATING EMERGENCY SHUTDOWN...{Style.RESET_ALL}")
        
        # Stop processing immediately
        self.is_processing = False
        self.running = False
        
        # Broadcast shutdown to all agents (if they listen)
        await self.bus.publish("SYSTEM_SHUTDOWN", {"reason": error_msg}, "GHOST")
        
        # Execute shutdown
        await self.shutdown()

    async def shutdown(self):
        print(f"\n{Fore.RED}[GHOST] SHUTDOWN PROTOCOL INITIATED.{Style.RESET_ALL}")
        self.running = False
        await kalshi_client.close()
        print(f"{Fore.RED}[GHOST] ALL SYSTEMS OFFLINE.{Style.RESET_ALL}")

    async def start_http_server(self):
        """HTTP server for triggering cycles and SSE streaming."""
        app = web.Application()
        
        # CORS middleware - restrict to specific origins
        ALLOWED_ORIGINS = [
            "http://localhost:3000",  # Dev frontend
            "http://127.0.0.1:3000",
        ]
        # Add production origins from env if set
        prod_origin = os.getenv("FRONTEND_ORIGIN")
        if prod_origin:
            ALLOWED_ORIGINS.append(prod_origin)

        async def cors_middleware(app, handler):
            async def middleware_handler(request):
                # Get origin from request
                origin = request.headers.get("Origin", "")

                # Handle preflight requests
                if request.method == "OPTIONS":
                    response = web.Response(status=200)
                else:
                    response = await handler(request)

                # Only allow specific origins, not wildcard
                if origin in ALLOWED_ORIGINS:
                    response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
                response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
                return response
            return middleware_handler

        # Add middlewares: CORS first, then auth
        app.middlewares.append(cors_middleware)
        app.middlewares.append(auth_manager.middleware)

        async def trigger_cycle(request):
            data = await request.json()
            is_paper = data.get("isPaperTrading", True)
            asyncio.create_task(self.execute_single_cycle(is_paper))
            return web.json_response(
                {
                    "status": "triggered",
                    "cycleId": self.cycle_count + 1,
                    "isProcessing": self.is_processing,
                }
            )

        async def activate_kill_switch(request):
            self.manual_kill_switch = True
            # FIX: Immediate Halt (Atomicity)
            self.is_processing = False
            self.cycle_count = 0
            self.last_cycle_time = None  # Rate limit tracking
            self.running = False
            
            await self.bus.publish(
                "SYSTEM_LOG",
                {
                    "level": "ERROR",
                    "message": "[GHOST] 💀 MANUAL KILL SWITCH ACTIVATED - Engine Halted",
                    "agent_id": 1,
                    "timestamp": datetime.now().isoformat(),
                },
                "GHOST",
            )
            return web.json_response(
                {"status": "killed", "message": "Manual Kill Switch Activated. Engine Halted."}
            )

        async def deactivate_kill_switch(request):
            self.manual_kill_switch = False
            await self.bus.publish(
                "SYSTEM_LOG",
                {
                    "level": "INFO",
                    "message": "[GHOST] 🟢 MANUAL KILL SWITCH DEACTIVATED",
                    "agent_id": 1,
                    "timestamp": datetime.now().isoformat(),
                },
                "GHOST",
            )
            return web.json_response(
                {"status": "active", "message": "Manual Kill Switch Deactivated."}
            )

        async def reset_system(request):
            self.manual_kill_switch = False
            self.is_processing = False
            self.running = False
            return web.json_response({"status": "reset"})

        async def cancel_cycle(request):
            """Gracefully cancel the current cycle and disable autopilot."""
            # Always allow cancellation to ensure we can stop runaway loops
            self.is_processing = False
            
            # 1. Stop Autopilot (Critical fix for "runaway train")
            await self.bus.publish("SYSTEM_CONTROL", {"action": "STOP_AUTOPILOT"}, "HTTP")
            self.running = False
            
            # --- HARDENING: Emergency Rollback on Cancellation ---
            self.vault.release_all_reservations()
            
            # 2. Reset System State
            await self.bus.publish(
                "SYSTEM_STATE",
                {"isProcessing": False, "activeAgentId": None},
                "GHOST",
            )
            
            # 3. Log Cancellation
            await self.bus.publish(
                "SYSTEM_LOG",
                {
                    "level": "WARN",
                    "message": "[GHOST] 🛑 Cycle cancelled by user. Autopilot DISABLED.",
                    "agent_id": 1,
                    "timestamp": datetime.now().isoformat(),
                },
                "GHOST",
            )

            return web.json_response({"status": "cancelled", "message": "Cycle cancelled and Autopilot disabled."})

        async def health_check(request):
            return web.json_response(
                {
                    "status": "healthy",
                    "agents": 4,
                    "cycle": self.cycle_count,
                    "balance": self.vault.current_balance / 100,
                }
            )

        async def start_autopilot(request):
            """Enable autonomous cycle looping."""
            data = await request.json()
            is_paper = data.get("isPaperTrading", True)
            await self.bus.publish("SYSTEM_CONTROL", {"action": "START_AUTOPILOT", "isPaperTrading": is_paper}, "HTTP")
            return web.json_response({"status": "autopilot_started", "mode": "AUTOPILOT"})

        async def stop_autopilot(request):
            """Disable autonomous cycle looping (Graceful Pause)."""
            await self.bus.publish("SYSTEM_CONTROL", {"action": "STOP_AUTOPILOT"}, "HTTP")
            return web.json_response({"status": "autopilot_stopped", "mode": "MANUAL"})

        async def autopilot_status(request):
            """Get current autopilot status."""
            return web.json_response({
                "autopilot_enabled": self.soul.autopilot_enabled if hasattr(self, "soul") else False,
                "is_paper_trading": self.soul.is_paper_trading if hasattr(self, "soul") else True,
                "is_locked_down": self.soul.is_locked_down if hasattr(self, "soul") else False,
                "is_processing": self.is_processing,
                "cycle_count": self.cycle_count,
            })

        async def stream_logs(request):
            """SSE stream for real-time logs with proper error handling."""
            response = web.StreamResponse(
                status=200,
                reason="OK",
                headers={
                    "Content-Type": "text/event-stream",
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    # CORS handled by middleware
                },
            )

            try:
                await response.prepare(request)
            except (ConnectionResetError, asyncio.CancelledError, OSError) as e:
                print(f"[GHOST] SSE connection error: {e}")
                return response

            queue = asyncio.Queue()
            self.sse_clients.add(queue)

            try:
                while True:
                    event = await queue.get()
                    data = json.dumps(event)
                    try:
                        await response.write(f"data: {data}\n\n".encode())
                    except (ConnectionResetError, asyncio.CancelledError, OSError):
                        # Client disconnected - benign error
                        # print(f"[GHOST] SSE client disconnected")
                        break
            except asyncio.CancelledError:
                pass
            finally:
                try:
                    self.sse_clients.remove(queue)
                except KeyError:
                    pass  # Already removed

            return response

        async def auth_handler(request):
            """Handle authentication check."""
            # Return actual session data from auth_manager
            # In 2-tier architecture, we check the auth_manager session state
            if auth_manager.authenticated:
                return web.json_response({
                    "isAuthenticated": True,
                    "user": {
                        "id": "user_1",
                        "email": "trader@sentient-alpha.com" if auth_manager.is_production else "demo@kalshi.com",
                        "name": "Sentient Trader" if auth_manager.is_production else "Demo Trader"
                    },
                    "mode": auth_manager.mode,
                    "is_production": auth_manager.is_production
                })
            return web.json_response({
                "isAuthenticated": False,
                "user": None,
                "mode": "demo",
                "is_production": False
            })

        async def get_pnl(request):
            """Get PnL history (simulated for now)."""
            # In a real scenario, query database for balance history
            current_balance = engine.vault.current_balance / 100
            
            # Generate mock history for the last 24h
            now = datetime.now()
            history = []
            for i in range(24):
                ts = now.timestamp() - (i * 3600)
                # Simulated fluctuation
                val = current_balance - (i * 5) 
                history.append({
                    "timestamp": datetime.fromtimestamp(ts).isoformat(),
                    "balance": val
                })
            
            return web.json_response({
                "currentBalance": current_balance,
                "history": history[::-1] # Oldest first
            })

        async def get_pnl_heatmap(request):
            """Get daily PnL heatmap."""
            # Mock data for heatmap
            heatmap = []
            import random
            today = datetime.now()
            for i in range(30): # Last 30 days
                date = today.timestamp() - (i * 86400)
                heatmap.append({
                    "date": datetime.fromtimestamp(date).strftime("%Y-%m-%d"),
                    "pnl": random.uniform(-50, 100),
                    "count": random.randint(1, 10)
                })
            return web.json_response({"heatmap": heatmap})

        async def get_env_health(request):
            """Verify 'Stay Alive' environment integrity."""
            import os
            
            # 1. Symlink Integrity
            opencode_skills_ok = os.path.islink(".opencode/skills")
            agent_workflows_ok = os.path.islink(".agent/workflows")
            
            # 2. Project Soul Status
            soul_path = "ai-env/soul/identity.md"
            soul_exists = os.path.exists(soul_path)
            last_snapshot = "No snapshot found."
            
            if soul_exists:
                try:
                    with open(soul_path) as f:
                        lines = f.readlines()
                        # Find the last snapshot (lines starting with **Snapshot**)
                        snapshots = [l for l in lines if l.startswith("**Snapshot**")]
                        if snapshots:
                            last_snapshot = snapshots[-1].replace("**Snapshot**: ", "").strip()
                except Exception as e:
                    last_snapshot = f"Error reading soul: {e}"

            return web.json_response({
                "symlinks": {
                    "opencode_skills": "OK" if opencode_skills_ok else "BROKEN",
                    "agent_workflows": "OK" if agent_workflows_ok else "BROKEN"
                },
                "project_soul": {
                    "exists": soul_exists,
                    "last_intuition": last_snapshot
                },
                "status": "HEALTHY" if (opencode_skills_ok and agent_workflows_ok and soul_exists) else "DEGRADED"
            })

        async def trigger_ragnarok(request):
            """Emergency protocol to liquidate all positions and lock the vault."""
            await execute_ragnarok()
            self.manual_kill_switch = True
            await self.bus.publish(
                "SYSTEM_LOG",
                {
                    "level": "ERROR",
                    "message": "[GHOST] RAGNAROK EXECUTED - All positions liquidated",
                    "agent_id": 1,
                    "timestamp": datetime.now().isoformat(),
                },
                "GHOST",
            )
            return web.json_response({"status": "ragnarok_executed", "message": "Emergency liquidation complete. Vault locked."})

        # Routes for direct access (port 3002)
        app.router.add_get("/env-health", get_env_health)
        app.router.add_post("/trigger", trigger_cycle)
        app.router.add_post("/kill-switch", activate_kill_switch)
        app.router.add_post("/deactivate-kill-switch", deactivate_kill_switch)
        app.router.add_post("/reset", reset_system)
        app.router.add_post("/cancel", cancel_cycle)
        app.router.add_post("/auth", auth_handler)
        app.router.add_get("/pnl", get_pnl)
        app.router.add_get("/pnl/heatmap", get_pnl_heatmap)
        app.router.add_post("/ragnarok", trigger_ragnarok)
        app.router.add_get("/health", health_check)
        app.router.add_post("/autopilot/start", start_autopilot)
        app.router.add_post("/autopilot/stop", stop_autopilot)
        app.router.add_get("/autopilot/status", autopilot_status)
        app.router.add_get("/stream", stream_logs)

        # Authentication endpoints
        from core.auth import login_handler, logout_handler, verify_handler
        app.router.add_post("/auth/login", login_handler)
        app.router.add_get("/auth/verify", verify_handler)
        app.router.add_post("/auth/logout", logout_handler)

        # Proxied routes (Vite proxy preserves /api prefix)
        app.router.add_get("/api/env-health", get_env_health)
        app.router.add_post("/api/trigger", trigger_cycle)
        app.router.add_post("/api/kill-switch", activate_kill_switch)
        app.router.add_post("/api/deactivate-kill-switch", deactivate_kill_switch)
        app.router.add_post("/api/reset", reset_system)
        app.router.add_post("/api/cancel", cancel_cycle)
        app.router.add_post("/api/auth", auth_handler)
        app.router.add_post("/api/auth/login", login_handler)
        app.router.add_get("/api/auth/verify", verify_handler)
        app.router.add_post("/api/auth/logout", logout_handler)
        app.router.add_get("/api/pnl", get_pnl)
        app.router.add_get("/api/pnl/heatmap", get_pnl_heatmap)
        app.router.add_post("/api/ragnarok", trigger_ragnarok)
        app.router.add_get("/api/health", health_check)
        app.router.add_post("/api/autopilot/start", start_autopilot)
        app.router.add_post("/api/autopilot/stop", stop_autopilot)
        app.router.add_get("/api/autopilot/status", autopilot_status)
        app.router.add_get("/api/stream", stream_logs)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", 3002)
        await site.start()

        print(f"{Fore.CYAN}[GHOST] HTTP Server online at http://0.0.0.0:3002{Style.RESET_ALL}")

        # Subscribe to bus events for SSE broadcast
        await self.bus.subscribe("SYSTEM_LOG", self._broadcast_to_sse)
        await self.bus.subscribe("VAULT_UPDATE", self._broadcast_to_sse)
        await self.bus.subscribe("SIM_RESULT", self._broadcast_to_sse)
        await self.bus.subscribe("SYSTEM_STATE", self._broadcast_to_sse)
        await self.bus.subscribe("SYSTEM_ERROR", self._broadcast_to_sse)  # Add error broadcasting

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
                    "id": f"log-{datetime.now().timestamp()}-{uuid.uuid4().hex[:8]}",
                    "timestamp": payload.get("timestamp", datetime.now().isoformat()),
                    "agentId": agent_id,
                    "cycleId": self.cycle_count,
                    "phaseId": phase_id,
                    "message": payload.get("message", ""),
                    "level": payload.get("level", "INFO"),
                },
            }
        elif event_type == "VAULT_UPDATE":
            formatted_event = {"type": "VAULT", "state": payload}
        elif event_type == "SIM_RESULT":
            formatted_event = {"type": "SIMULATION", "state": payload}
        elif event_type == "SYSTEM_STATE":
            formatted_event = {"type": "STATE", "state": payload}
        elif event_type == "SYSTEM_ERROR":
            # Map agent_name to agent_id for phase mapping
            agent_name = payload.get("agent_name", "")
            agent_id_map = {
                "SOUL": 1,
                "SENSES": 2,
                "BRAIN": 3,
                "HAND": 4,
                "GATEWAY": 5
            }
            agent_id = agent_id_map.get(agent_name, 1)
            phase_id = AGENT_TO_PHASE.get(agent_id, 1)

            formatted_event = {
                "type": "ERROR",
                "error": {
                    "id": f"error-{datetime.now().timestamp()}-{uuid.uuid4().hex[:8]}",
                    "timestamp": payload.get("timestamp", datetime.now().isoformat()),
                    "agentId": agent_id,
                    "cycleId": self.cycle_count,
                    "phaseId": phase_id,
                    "code": payload.get("code", "UNKNOWN_ERROR"),
                    "message": payload.get("message", "An error occurred"),
                    "severity": payload.get("severity", "MEDIUM"),
                    "domain": payload.get("domain", "SYSTEM"),
                    "hint": payload.get("hint", ""),
                    "context": payload.get("context", {}),
                }
            }

        if formatted_event:
            # Use list() to create a snapshot since we might modify during iteration
            for queue in list(self.sse_clients):
                try:
                    await queue.put(formatted_event)
                except Exception:
                    # Client disconnected, remove from set
                    self.sse_clients.discard(queue)

    async def run(self):
        """Main event loop."""
        await self.initialize_system()
        await self.start_http_server()

        while self.running:
            await asyncio.sleep(1)

    def start(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Signal handling - Windows compatible approach
        try:
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, lambda: asyncio.create_task(self.shutdown()))
        except NotImplementedError:
            # Windows doesn't support add_signal_handler, use default signal handling
            pass

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
