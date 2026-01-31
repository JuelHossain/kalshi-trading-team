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
from datetime import datetime

from aiohttp import web
from colorama import Fore, Style, init
from dotenv import load_dotenv

# Load Env BEFORE imports
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Agent imports
from agents.base import BaseAgent
from agents.brain import BrainAgent
from agents.gateway import GatewayAgent
from agents.hand import HandAgent
from agents.senses import SensesAgent
from agents.soul import SoulAgent

# Core imports
from core.auth import auth_manager
from core.bus import EventBus
from core.constants import (
    MIN_CYCLE_INTERVAL_SECONDS,
    AGENT_ID_SOUL,
    AGENT_ID_SENSES,
    AGENT_ID_BRAIN,
    AGENT_ID_HAND,
    AGENT_ID_GATEWAY,
)
from core.logger import get_logger
from core.network import kalshi_client
from core.synapse import Synapse
from core.vault import RecursiveVault

# HTTP imports
from http_api.server import setup_middlewares, start_server
from http_api.routes import register_all_routes, register_sse_subscriptions

import config

# Initialize Logger
logger = get_logger("GHOST")



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
        logger.info("==========================================")
        logger.info("   GHOST ENGINE v3.0 (4 MEGA-AGENTS)     ")
        logger.info("==========================================")

        # Autopilot / Request Cycle Support
        await self.bus.subscribe("REQUEST_CYCLE", self._handle_cycle_request)

        # Fail-Fast Protocol
        await self.bus.subscribe("SYSTEM_FATAL", self._handle_system_fatal)

        # Initialize 4 Mega-Agents
        print(f"{Fore.CYAN}[GHOST] Initializing 4 Mega-Agent Pillars...{Style.RESET_ALL}")

        try:
            # Initialize 4 Mega-Agents using a helper pattern
            agent_configs = [
                (SoulAgent, AGENT_ID_SOUL, {"vault": self.vault, "synapse": self.synapse}),
                (SensesAgent, AGENT_ID_SENSES, {"kalshi_client": kalshi_client, "synapse": self.synapse}),
                (BrainAgent, AGENT_ID_BRAIN, {"synapse": self.synapse}),
                (HandAgent, AGENT_ID_HAND, {"vault": self.vault, "kalshi_client": kalshi_client, "synapse": self.synapse}),
                (GatewayAgent, AGENT_ID_GATEWAY, {"vault": self.vault}),
            ]

            for agent_class, agent_id, kwargs in agent_configs:
                agent = agent_class(agent_id, self.bus, **kwargs)
                await agent.start()
                self.agents.append(agent)

        except Exception as e:
            logger.error(f"Failed to initialize agents: {e}")

        # Initialize Vault with Real Balance
        try:
            real_balance = await kalshi_client.get_balance()
            print(f"{Fore.GREEN}[SOUL] Fetched Real Balance: ${real_balance/100:.2f}{Style.RESET_ALL}")
            await self.vault.initialize(real_balance)
        except Exception as e:
            print(f"{Fore.RED}[SOUL] Failed to fetch balance: {e}. Defaulting to $0 (Safety Mode).{Style.RESET_ALL}")
            await self.vault.initialize(0)

        print(f"{Fore.GREEN}[GHOST] SYSTEM ONLINE - 4 Pillars Active.{Style.RESET_ALL}")

    def _halt(self, reason: str) -> bool:
        """Print halt message and return False (helper for kill switch checks)."""
        print(f"{Fore.RED}[GHOST] {reason}{Style.RESET_ALL}")
        return False

    async def authorize_cycle(self) -> bool:
        """
        SOUL: Strategic Authorization
        Checks Kill Switch and safety conditions.
        """
        # Temporarily disabled for manual testing
        if self.last_cycle_time:
            elapsed = (datetime.now() - self.last_cycle_time).total_seconds()
            if elapsed < MIN_CYCLE_INTERVAL_SECONDS:
                logger.warning(f"Rate limit: Wait {MIN_CYCLE_INTERVAL_SECONDS - elapsed:.0f}s before next cycle.")
                return False

        if self.manual_kill_switch:
            return self._halt("MANUAL KILL SWITCH ACTIVE. HALTING.")

        if os.getenv("KILL_SWITCH") == "true":
            return self._halt("ENV KILL SWITCH ACTIVE. HALTING.")

        if self.vault.kill_switch_active:
            return self._halt("VAULT KILL SWITCH ACTIVE. HALTING.")

        # Soul Lockdown Check (API Failure / Hard Floor)
        if hasattr(self, "soul") and self.soul.is_locked_down:
            return self._halt("SOUL LOCKDOWN ACTIVE. HALTING.")

        # Synapse Error Box Check (Strict Decoupling)
        if hasattr(self, "synapse") and self.synapse:
            error_count = await self.synapse.errors.size()
            if error_count > 0:
                return self._halt(f"ERROR BOX ACTIVE ({error_count} errors). HALTING.")

        # 1. Hard floor check ($255) - ATOMIC with vault update
        try:
            real_balance = await kalshi_client.get_balance()

            # UPDATE VAULT FIRST, then check - ensures atomic read-check
            self.vault.current_balance = real_balance

            if real_balance < self.vault.HARD_FLOOR_CENTS:
                return self._halt(f"HARD FLOOR BREACH (${real_balance/100:.2f} < ${self.vault.HARD_FLOOR_CENTS/100:.2f}). EMERGENCY LOCKDOWN.")
                return False
        except Exception:
            # Fallback to vault cache if API fails
            if self.vault.current_balance < self.vault.HARD_FLOOR_CENTS:
                return False

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
                    "message": f"CYCLE #{self.cycle_count} COMPLETE",
                    "agent_id": 1,
                    "timestamp": datetime.now().isoformat(),
                },
                "GHOST",
            )

            logger.info(f"Cycle {self.cycle_count} complete.")

        except Exception as e:
            logger.error(f"Cycle {self.cycle_count} failed: {e}")

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

        print(f"\n{Fore.RED}[GHOST] FATAL ERROR reported by {agent_id}: {error_msg}{Style.RESET_ALL}")
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

        # Setup middlewares
        setup_middlewares(app, auth_manager)

        # Register all routes
        register_all_routes(app, self)

        # Start server
        await start_server(app)

        # Register SSE subscriptions
        register_sse_subscriptions(self)

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
