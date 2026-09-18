"""
MEGA-AGENT 1: THE SOUL
Role: Executive Director & Self-Healing Core

Core SoulAgent class with evolution and lifecycle management.
"""

import asyncio
from typing import Any

from agents.base import BaseAgent
from core.ai_utils import initialize_gemini_client
from core.bus import EventBus
from core.db import check_connection as check_supabase_connection
from core.error_dispatcher import ErrorSeverity
from core.network import kalshi_client
from core.shared_utils import fire_and_forget
from core.synapse import Synapse
from core.vault import RecursiveVault
from core.vault_utils import check_hard_floor_breach, publish_vault_state

from .evolution import evolve_instructions


class SoulAgent(BaseAgent):
    """The Executive Director - System, Memory & Evolution"""

    def __init__(
        self,
        agent_id: int,
        bus: EventBus,
        vault: RecursiveVault,
        synapse: Synapse = None,
        error_manager=None,
    ):
        super().__init__("SOUL", agent_id, bus, synapse, error_manager)
        self.vault = vault
        self.trading_instructions = ""
        self.mistakes_log = []
        self.strengths_list = []
        self.is_locked_down = False
        self.autopilot_enabled = False
        self.autopilot_delay = 30
        self.is_paper_trading = True
        self._pulse_task: asyncio.Task | None = None

        # Initialize Gemini for self-evolution
        self.client, self.ai_client, self.gemini_model, self._gemini_available = (
            initialize_gemini_client(log_callback=self.log, bus=self.bus)
        )

        self._first_run = True

    async def setup(self):
        """Subscribe to cycle lifecycle, trade results and control events."""
        await self.log("Soul awakening. Executive Director online.")

        await self.bus.subscribe("CYCLE_START", self.on_cycle_start)
        await self.bus.subscribe("TRADE_RESULT", self.on_trade_result)
        await self.bus.subscribe("CYCLE_COMPLETE", self.on_cycle_complete)
        await self.bus.subscribe("SYSTEM_CONTROL", self.on_system_control)
        await self.bus.subscribe("SYSTEM_LOCKDOWN", self.on_system_lockdown)
        await self.bus.subscribe("SYSTEM_SHUTDOWN", self.on_system_shutdown)
        await self.bus.subscribe("SYSTEM_FATAL", self.on_system_fatal)

    async def on_cycle_start(self, message):
        """Pre-flight sequence"""
        await self.log("Initiating pre-flight sequence...")

        # 0. Lazy Load API Check (First Run Only)
        if self._first_run:
            await self.check_api_health()
            if self.is_locked_down:
                return
            self._first_run = False

        # 1. Safety Check - Hard Floor
        is_breached, error_msg = check_hard_floor_breach(self.vault)
        if is_breached:
            await self.log(f"EMERGENCY: {error_msg}", level="ERROR")
            self.is_locked_down = True
            await self.bus.publish("SYSTEM_LOCKDOWN", {"reason": "Hard floor breach"}, self.name)
            return

        # 2. Health Check
        await self.log("Health check: All systems nominal.")

        # 3. Publish pre-flight complete
        await self.bus.publish(
            "PREFLIGHT_COMPLETE",
            {
                "balance": self.vault.current_balance,
                "is_locked": self.is_locked_down,
                "instructions": (
                    self.trading_instructions[:200] if self.trading_instructions else "Default"
                ),
            },
            self.name,
        )

        await self.log("Pre-flight complete. Handing off to SENSES.")

    async def on_trade_result(self, message):
        """Learn from trade outcomes for self-evolution"""
        payload = message.payload
        outcome = payload.get("outcome", "unknown")
        details = payload.get("details", "")

        # Only a settled outcome is a lesson. The Hand publishes TRADE_RESULT
        # with outcome "pending" the moment an order fills, before the game
        # is played; the old else-branch filed every one of those as a loss
        # and evolve_instructions then rewrote the trading rules from a
        # mistakes log full of trades that had not resolved.
        if outcome == "win":
            self.strengths_list.append(details)
            await self.log(f"Win recorded. Strength: {details[:50]}...")
        elif outcome == "loss":
            self.mistakes_log.append(details)
            await self.log(f"Loss recorded. Lesson: {details[:50]}...")
        else:
            await self.log(f"Trade opened, outcome {outcome}: {details[:50]}", level="DEBUG")

    async def evolve_instructions(self):
        """Use Gemini to rewrite trading instructions based on history"""
        new_instructions = await evolve_instructions(
            client=self.client,
            ai_client=self.ai_client,
            trading_instructions=self.trading_instructions,
            strengths_list=self.strengths_list,
            mistakes_log=self.mistakes_log,
            log_callback=self.log,
        )

        if new_instructions:
            self.trading_instructions = new_instructions

    async def on_system_control(self, message):
        """Handle system-wide control commands (Autopilot, Kill Switch)"""
        action = message.payload.get("action")
        if action == "START_AUTOPILOT":
            self.autopilot_enabled = True
            self.is_paper_trading = message.payload.get("isPaperTrading", True)
            await self.log(
                f"AUTOPILOT ENABLED (Paper: {self.is_paper_trading}). Starting autonomous loop..."
            )
            await self.bus.publish(
                "REQUEST_CYCLE", {"isPaperTrading": self.is_paper_trading}, self.name
            )
        elif action == "STOP_AUTOPILOT":
            self._cancel_pulse()
            if self.autopilot_enabled:
                self.autopilot_enabled = False
                await self.log("AUTOPILOT DISABLED. (System will pause after current cycle)")

    async def on_cycle_complete(self, message):
        """Schedule the next cycle if in Autopilot mode.

        The pulse is detached (fire_and_forget) rather than slept inline, so
        the 30s wait does not hold up the CYCLE_COMPLETE publisher. There is
        only ever one pending pulse: a cycle that completes while one is
        waiting -- a manual /trigger, or STOP then START inside the delay --
        replaces it instead of starting a second chain that would run the
        engine at twice the configured cadence from then on.
        """
        if self.autopilot_enabled and not self.is_locked_down:
            await self.log(f"Cycle complete. Waiting {self.autopilot_delay}s for next pulse...")
            self._cancel_pulse()
            self._pulse_task = fire_and_forget(self._pulse())

    async def _pulse(self):
        """Wait out the autopilot delay, then request the next cycle if still enabled."""
        await asyncio.sleep(self.autopilot_delay)
        if self.autopilot_enabled and not self.is_locked_down:
            await self.bus.publish(
                "REQUEST_CYCLE", {"isPaperTrading": self.is_paper_trading}, self.name
            )

    def _cancel_pulse(self) -> None:
        """Drop the pending pulse, if any (never the task we are running in)."""
        if self._pulse_task is not None and self._pulse_task is not asyncio.current_task():
            self._pulse_task.cancel()
        self._pulse_task = None

    async def teardown(self):
        """Stop autopilot so a stopped Soul cannot request another cycle.

        Disabling as well as cancelling matters: a cycle still in flight will
        publish CYCLE_COMPLETE after this returns, and with autopilot still on
        that would arm a fresh pulse.
        """
        self.autopilot_enabled = False
        self._cancel_pulse()

    async def on_system_lockdown(self, message):
        """Handle system lockdown by disabling autopilot immediately"""
        reason = message.payload.get("reason", "Unknown")
        await self.log(f"SYSTEM LOCKDOWN: {reason}", level="WARN")
        self.is_locked_down = True
        self.autopilot_enabled = False
        await self.log("AUTOPILOT DISABLED due to lockdown")

    async def on_system_shutdown(self, message):
        """Handle system shutdown by disabling autopilot immediately"""
        reason = message.payload.get("reason", "Unknown")
        await self.log(f"SYSTEM SHUTDOWN: {reason}", level="WARN")
        self.autopilot_enabled = False
        await self.log("AUTOPILOT DISABLED due to shutdown")

    async def on_system_fatal(self, message):
        """Handle fatal errors by disabling autopilot immediately"""
        error_msg = message.payload.get("message", "Unknown Fatal Error")
        await self.log(f"FATAL ERROR: {error_msg}", level="ERROR")
        self.is_locked_down = True
        self.autopilot_enabled = False
        await self.log("AUTOPILOT DISABLED due to fatal error")

    async def on_tick(self, payload: dict[str, Any]):
        """Periodic self-check"""
        await publish_vault_state(self.bus, self.vault, self.name)

    async def check_api_health(self):
        """Verify all critical APIs are reachable and functional."""
        await self.log("Requesting Pre-flight API Status Check...", level="INFO")

        errors = []

        # 1. Kalshi API Check
        try:
            balance = await kalshi_client.get_balance()
            if balance == 0 and not await kalshi_client.get_active_markets(limit=1):
                errors.append("Kalshi API unreachable or 0 balance/markets.")
        except Exception as e:
            errors.append(f"Kalshi API Error: {e}")

        # 2. Supabase Check
        # Analytics only -- no trading decision reads from it. Treating it as
        # fatal meant a dead or paused project locked the engine down at
        # pre-flight and no cycle could run, which is a strictly worse outcome
        # than trading without a metrics sink.
        supabase_ok = await check_supabase_connection()
        if not supabase_ok:
            await self.log(
                "Supabase unreachable - continuing without the analytics sink.",
                level="WARN",
            )

        # 3. Gemini Check
        gemini_ok = await self._probe_gemini()

        if errors:
            error_msg = " | ".join(errors)
            await self.log(f"OPENING PRE-FLIGHT CHECK FAILED: {error_msg}", level="ERROR")

            await self.log_error(
                code="SYSTEM_INIT_FAILED",
                message=f"Pre-flight API Failures: {error_msg}",
                severity=ErrorSeverity.CRITICAL,
                hint="Check API keys for Kalshi/Gemini/OpenRouter and DB connection",
            )

            self.is_locked_down = True
            await self.bus.publish(
                "SYSTEM_LOCKDOWN", {"reason": f"API Check Failed: {error_msg}"}, self.name
            )
            await self.bus.publish(
                "SYSTEM_FATAL", {"message": f"Pre-flight Check Failed: {error_msg}"}, self.name
            )
        else:
            passed = (
                ["Kalshi"]
                + (["Supabase"] if supabase_ok else [])
                + (["Gemini"] if gemini_ok else [])
            )
            await self.log(
                f"PRE-FLIGHT API CHECK PASSED ({', '.join(passed)})",
                level="SUCCESS" if gemini_ok else "WARN",
            )

    async def _probe_gemini(self) -> bool:
        """Ask the model the Brain will use, the way it will ask, with no fallback.

        This used to go through generate_with_fallback, which tries five models
        and then OpenRouter, so any OpenRouter reply reported "Gemini PASSED".
        Seen live on 2026-09-18: five "API key not valid" failures, then
        PRE-FLIGHT API CHECK PASSED -- with a stale shell key overriding the
        real one, and every Brain estimate failing after it.

        A failure is logged, not added to the pre-flight errors: those publish
        SYSTEM_FATAL, which ends the process, and under systemd a Gemini outage
        at boot would become a restart loop. The Brain vetoes every market
        while grounded Gemini is unavailable, so continuing costs nothing.
        """
        import os

        from agents.brain.debate import build_grounding_config

        if not self.client:
            if self._gemini_available:
                await self.log(
                    "Gemini API key missing: the Brain will veto every market.", level="ERROR"
                )
            return False

        model = os.environ.get("GEMINI_MODEL") or self.gemini_model
        grounding = build_grounding_config()
        detail = "empty reply"
        try:
            response = await asyncio.get_running_loop().run_in_executor(
                None,
                lambda: self.client.models.generate_content(
                    model=model, contents="ping", config=grounding
                ),
            )
            if response is not None and response.text:
                return True
        except Exception as e:
            detail = str(e)[:160]

        consequence = (
            "the Brain will veto every market until it answers"
            if grounding is not None
            else "Brain estimates will come from the ungrounded OpenRouter fallback"
        )
        await self.log(
            f"Gemini ({model}{', grounded' if grounding is not None else ''}) unavailable: "
            f"{detail} -- {consequence}.",
            level="ERROR",
        )
        return False
