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
    AGENT_ID_BRAIN,
    AGENT_ID_GATEWAY,
    AGENT_ID_HAND,
    AGENT_ID_SENSES,
    AGENT_ID_SOUL,
    MIN_CYCLE_INTERVAL_SECONDS,
)
from core.display import (
    GhostDisplay,
    AgentType,
    get_display,
    show_startup_banner,
    show_agent_status,
    update_agent_status,
    log_info,
    log_success,
    log_warning,
    log_error,
    log_critical,
    show_error,
)
from core.error_codes import ErrorDomain, ErrorSeverity
from core.error_manager import ErrorManager, get_error_manager, set_error_manager
from core.logger import get_logger
from core.network import kalshi_client
from core.synapse import Synapse
from core.vault import RecursiveVault
from http_api.routes import register_all_routes, register_sse_subscriptions

# HTTP imports
from http_api.server import setup_middlewares, start_server

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

        # Display system
        self.display: GhostDisplay = get_display()

        # Initialize ErrorManager with shutdown callback
        self.error_manager = ErrorManager(
            shutdown_callback=self.shutdown,
            console=self.display.console,
        )
        set_error_manager(self.error_manager)



    async def initialize_system(self):
        # Show the Rich startup banner
        show_startup_banner()

        log_info("Initializing Ghost Engine v3.0 system components...")

        # Autopilot / Request Cycle Support
        await self.bus.subscribe("REQUEST_CYCLE", self._handle_cycle_request)

        # Fail-Fast Protocol
        await self.bus.subscribe("SYSTEM_FATAL", self._handle_system_fatal)

        # Initialize 4 Mega-Agents
        log_info("Initializing 4 Mega-Agent Pillars...")

        try:
            # Initialize 4 Mega-Agents using a helper pattern
            agent_configs = [
                (SoulAgent, AGENT_ID_SOUL, AgentType.SOUL, {"vault": self.vault, "synapse": self.synapse}),
                (SensesAgent, AGENT_ID_SENSES, AgentType.SENSES, {"kalshi_client": kalshi_client, "synapse": self.synapse}),
                (BrainAgent, AGENT_ID_BRAIN, AgentType.BRAIN, {"synapse": self.synapse}),
                (HandAgent, AGENT_ID_HAND, AgentType.HAND, {"vault": self.vault, "kalshi_client": kalshi_client, "synapse": self.synapse}),
                (GatewayAgent, AGENT_ID_GATEWAY, AgentType.GATEWAY, {"vault": self.vault}),
            ]

            for agent_class, agent_id, agent_type, kwargs in agent_configs:
                update_agent_status(agent_type, "INITIALIZING")
                # Pass error_manager to each agent
                kwargs["error_manager"] = self.error_manager
                agent = agent_class(agent_id, self.bus, **kwargs)
                await agent.start()
                self.agents.append(agent)
                log_success(f"{agent_type.name} initialized successfully", agent_type)
                update_agent_status(agent_type, "IDLE")

        except Exception as e:
            log_error(f"Failed to initialize agents: {e}")
            show_error(
                title="Agent Initialization Failed",
                message=str(e),
                context="Failed to initialize one or more Mega-Agents during system startup.",
                hint="Check agent configurations and dependencies.",
                severity="ERROR"
            )
            # Register critical error with ErrorManager (will shutdown engine)
            await self.error_manager.register_error(
                code="SYSTEM_INIT_FAILED",
                message=f"Failed to initialize agents: {e}",
                severity=ErrorSeverity.CRITICAL,
                domain=ErrorDomain.SYSTEM,
                agent_name="GHOST",
                exception=e,
                hint="Check agent configurations and dependencies"
            )

        # Initialize Vault with Real Balance
        try:
            real_balance = await kalshi_client.get_balance()
            log_info(f"Fetched Real Balance: ${real_balance/100:.2f}", AgentType.SOUL)
            await self.vault.initialize(real_balance)
            update_agent_status(AgentType.SOUL, "BALANCE_LOADED")
        except Exception as e:
            log_warning(f"Failed to fetch balance: {e}. Defaulting to $0 (Safety Mode).", AgentType.SOUL)
            show_error(
                title="Balance Fetch Failed",
                message=str(e),
                context="Could not fetch real balance from Kalshi API. Using $0 default.",
                hint="Check API credentials and network connection.",
                severity="WARNING",
                agent=AgentType.SOUL
            )
            await self.vault.initialize(0)

        # Show system online message
        self.display.show_system_online()

        # Update display with final agent status
        show_agent_status()

    def _halt(self, reason: str) -> bool:
        """Print halt message and return False (helper for kill switch checks)."""
        log_critical(reason, AgentType.SOUL)
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
            log_warning("Cycle already in progress. Ignoring.")
            return

        self.is_processing = True

        # Use Rich progress display for the cycle
        with self.display.cycle_progress(self.cycle_count + 1, is_paper_trading) as progress:
            try:
                # SOUL: Authorization Check
                update_agent_status(AgentType.SOUL, "AUTHORIZING")
                progress.update_phase("soul", 25)

                if not await self.authorize_cycle():
                    msg = f"Cycle {self.cycle_count + 1} not authorized."
                    log_warning(msg)
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

                progress.complete_phase("soul")
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
                update_agent_status(AgentType.SOUL, "ACTIVE")
                await self.bus.publish(
                    "CYCLE_START",
                    {"cycle": self.cycle_count, "isPaperTrading": is_paper_trading},
                    "GHOST",
                )

                # SENSES: Market Surveillance
                update_agent_status(AgentType.SENSES, "SCANNING")
                progress.update_phase("senses", 50)
                await asyncio.sleep(0.2)
                progress.complete_phase("senses")

                # BRAIN: Intelligence Analysis
                update_agent_status(AgentType.BRAIN, "ANALYZING")
                progress.update_phase("brain", 50)
                await asyncio.sleep(0.2)
                progress.complete_phase("brain")

                # HAND: Execution & Trading
                update_agent_status(AgentType.HAND, "EXECUTING")
                progress.update_phase("hand", 50)
                await asyncio.sleep(0.2)

                # Broadcast TICK for periodic updates
                await self.bus.publish(
                    "TICK", {"cycle": self.cycle_count, "isPaperTrading": is_paper_trading}, "GHOST"
                )

                progress.complete_phase("hand")

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

                log_info(f"Cycle {self.cycle_count} complete.")

            except Exception as e:
                log_error(f"Cycle {self.cycle_count} failed: {e}")
                show_error(
                    title="Cycle Execution Failed",
                    message=str(e),
                    context=f"Trading cycle #{self.cycle_count} encountered an error during execution.",
                    hint="Check agent logs and system state for details.",
                    severity="ERROR"
                )

            finally:
                self.is_processing = False

                # Reset agent statuses
                for agent_type in [AgentType.SOUL, AgentType.SENSES, AgentType.BRAIN, AgentType.HAND]:
                    update_agent_status(agent_type, "IDLE")

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

        log_critical(f"FATAL ERROR reported by {agent_id}: {error_msg}", AgentType.SOUL)
        log_critical("INITIATING EMERGENCY SHUTDOWN...", AgentType.SOUL)

        # Stop processing immediately
        self.is_processing = False
        self.running = False

        # Broadcast shutdown to all agents (if they listen)
        await self.bus.publish("SYSTEM_SHUTDOWN", {"reason": error_msg}, "GHOST")

        # Execute shutdown
        await self.shutdown()

    async def shutdown(self, reason: str = "Manual shutdown"):
        """
        Shutdown the engine gracefully

        Args:
            reason: The reason for the shutdown
        """
        log_critical(f"SHUTDOWN PROTOCOL INITIATED: {reason}")
        self.running = False

        # Update all agent statuses to shutdown
        for agent_type in AgentType:
            update_agent_status(agent_type, "SHUTTING_DOWN")

        # Shutdown all agents
        for agent in self.agents:
            try:
                if hasattr(agent, 'teardown'):
                    await agent.teardown()
            except Exception as e:
                log_error(f"Error during agent teardown: {e}")

        await kalshi_client.close()

        # Show shutdown message
        self.display.show_shutdown_message()

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
