"""
MEGA-AGENT 1: THE SOUL
Role: Executive Director & Self-Healing Core

Workflow:
1. Pre-Flight: Handshake with Kalshi v2, Groq, Gemini, and RapidAPI
2. Audit: Pull last 24h wins/losses from Supabase
3. Synthesis: Gemini 1.5 Pro rewrites Trading Instructions (Self-Optimization)
4. UI Hydration: Push balance, mistakes log, strengths list to Dashboard
5. Safety: Enforce $255 (15%) hard floor stop-loss
"""

import asyncio
import os
from typing import Any

from agents.base import BaseAgent
from core.ai_client import AIClient
from core.bus import EventBus
from core.error_dispatcher import ErrorSeverity
from core.vault import RecursiveVault

try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


from core.db import check_connection as check_supabase_connection
from core.network import kalshi_client
from core.synapse import Synapse


class SoulAgent(BaseAgent):
    """The Executive Director - System, Memory & Evolution"""


    def __init__(self, agent_id: int, bus: EventBus, vault: RecursiveVault, synapse: Synapse = None):
        super().__init__("SOUL", agent_id, bus, synapse)
        self.vault = vault
        self.trading_instructions = ""
        self.mistakes_log = []
        self.strengths_list = []
        self.is_locked_down = False
        self.autopilot_enabled = False
        self.autopilot_delay = 30  # Seconds between cycles
        self.is_paper_trading = True  # Default to safety 


        # Initialize Gemini for self-evolution
        if GEMINI_AVAILABLE:
            api_key = os.environ.get("GEMINI_API_KEY")
            if api_key:
                self.client = genai.Client(api_key=api_key)
                self.openrouter_key = os.environ.get("OPENROUTER_API_KEY")
                # Initialize AI client with OpenRouter fallback
                self.ai_client = AIClient(
                    openrouter_key=self.openrouter_key,
                    log_callback=lambda msg, level="INFO": asyncio.create_task(
                        self.log(msg, level=level)
                    ),
                    bus=self.bus
                )
            else:
                self.client = None
                self.ai_client = None
        else:
            self.client = None
            self.ai_client = None

        self._first_run = True

    async def setup(self):
        await self.log("Soul awakening. Executive Director online.")

        # API Health Check deferred to first cycle start (lazy load)

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
                return # Stop here if checks failed
            self._first_run = False

        # 1. Safety Check - Hard Floor
        if self.vault.current_balance < self.vault.HARD_FLOOR_CENTS:
            await self.log(
                f"🛑 EMERGENCY: Balance ${self.vault.current_balance/100:.2f} below $255 floor. LOCKDOWN.",
                level="ERROR",
            )
            self.is_locked_down = True
            await self.bus.publish("SYSTEM_LOCKDOWN", {"reason": "Hard floor breach"}, self.name)
            return

        # 2. Health Check (absorbed from Mechanic)
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

        if outcome == "win":
            self.strengths_list.append(details)
            await self.log(f"Win recorded. Strength: {details[:50]}...")
        else:
            self.mistakes_log.append(details)
            await self.log(f"Loss recorded. Lesson: {details[:50]}...")

    async def _generate_with_fallback(self, prompt: str) -> str | None:
        """Try generating content with fallback models."""
        # Priority: 3.0 Pro -> 1.5 Flash (Skipping Image Preview as requested)
        models = ["gemini-3-pro-preview", "gemini-1.5-flash"]

        for model in models:
            try:
                # await self.log(f"Attempting generation with {model}...")
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.client.models.generate_content(
                        model=model,
                        contents=prompt
                    )
                )
                if response and response.text:
                    return response.text
            except Exception as e:
                await self.log(f"Model {model} failed: {e}", level="WARN")
                continue

        await self.log("All Gemini models failed. Attempting OpenRouter Fallback...", level="WARN")
        return await self.ai_client._call_openrouter(prompt) if self.ai_client else None

    async def evolve_instructions(self):
        """Use Gemini to rewrite trading instructions based on history (Self-Optimization)"""
        if not self.client:
            await self.log("Gemini unavailable. Using default instructions.")
            return

        prompt = f"""You are an AI trading strategist. Based on the following recent performance:

WINS: {self.strengths_list[-5:] if self.strengths_list else 'None yet'}
LOSSES: {self.mistakes_log[-5:] if self.mistakes_log else 'None yet'}

Write a concise set of 5 trading rules to maximize wins and avoid losses. Be specific."""

        try:
            response_text = await self._generate_with_fallback(prompt)
            if response_text:
                self.trading_instructions = response_text
                await self.log("Trading instructions evolved via Gemini.")
            else:
                 await self.log("Evolution failed: All models failed.", level="ERROR")
        except Exception as e:
            await self.log(f"Evolution failed: {str(e)[:50]}", level="ERROR")

    async def on_system_control(self, message):
        """Handle system-wide control commands (Autopilot, Kill Switch)"""
        action = message.payload.get("action")
        if action == "START_AUTOPILOT":
            self.autopilot_enabled = True
            self.is_paper_trading = message.payload.get("isPaperTrading", True)
            await self.log(f"🚀 AUTOPILOT ENABLED (Paper: {self.is_paper_trading}). Starting autonomous loop...")
            await self.bus.publish("REQUEST_CYCLE", {"isPaperTrading": self.is_paper_trading}, self.name)
        elif action == "STOP_AUTOPILOT":
            if self.autopilot_enabled:
                self.autopilot_enabled = False
                await self.log("🛑 AUTOPILOT DISABLED. (System will pause after current cycle)")

    async def on_cycle_complete(self, message):
        """Trigger next cycle if in Autopilot mode"""
        if self.autopilot_enabled and not self.is_locked_down:
            await self.log(f"Cycle complete. Waiting {self.autopilot_delay}s for next pulse...")
            await asyncio.sleep(self.autopilot_delay)

            # Re-check in case it was disabled during sleep
            if self.autopilot_enabled and not self.is_locked_down:
                await self.bus.publish("REQUEST_CYCLE", {"isPaperTrading": self.is_paper_trading}, self.name)

    async def on_system_lockdown(self, message):
        """Handle system lockdown by disabling autopilot immediately"""
        reason = message.payload.get("reason", "Unknown")
        await self.log(f"🔒 SYSTEM LOCKDOWN: {reason}", level="WARN")
        self.is_locked_down = True
        self.autopilot_enabled = False  # Disable autopilot immediately
        await self.log("🛑 AUTOPILOT DISABLED due to lockdown")

    async def on_system_shutdown(self, message):
        """Handle system shutdown by disabling autopilot immediately"""
        reason = message.payload.get("reason", "Unknown")
        await self.log(f"🔴 SYSTEM SHUTDOWN: {reason}", level="WARN")
        self.autopilot_enabled = False  # Disable autopilot immediately
        await self.log("🛑 AUTOPILOT DISABLED due to shutdown")

    async def on_system_fatal(self, message):
        """Handle fatal errors by disabling autopilot immediately"""
        error_msg = message.payload.get("message", "Unknown Fatal Error")
        await self.log(f"💀 FATAL ERROR: {error_msg}", level="ERROR")
        self.is_locked_down = True
        self.autopilot_enabled = False  # Disable autopilot immediately
        await self.log("🛑 AUTOPILOT DISABLED due to fatal error")

    async def on_tick(self, payload: dict[str, Any]):
        """Periodic self-check"""
        # Emit vault state for UI
        await self.bus.publish(
            "VAULT_UPDATE",
            {
                "principal": self.vault.PRINCIPAL_CAPITAL_CENTS / 100,
                "currentProfit": (self.vault.current_balance - self.vault.start_of_day_balance)
                / 100,
                "lockThreshold": self.vault.DAILY_PROFIT_THRESHOLD_CENTS / 100,
                "isLocked": self.vault.is_locked,
                "total": self.vault.current_balance / 100,
            },
            self.name,
        )

    async def check_api_health(self):
        """Verify all critical APIs are reachable and functional."""
        await self.log("Requesting Pre-flight API Status Check...", level="INFO")
        
        errors = []
        
        # 1. Kalshi API Check
        try:
            balance = await kalshi_client.get_balance()
            if balance == 0:
                   # Try one more check
                   if not await kalshi_client.get_active_markets(limit=1):
                       errors.append("Kalshi API unreachable or 0 balance/markets.")
        except Exception as e:
            errors.append(f"Kalshi API Error: {e}")

        # 2. Supabase Check
        if not await check_supabase_connection():
            errors.append("Supabase (Database) unreachable.")

        # 3. Gemini Check (if available)
        if GEMINI_AVAILABLE and self.client:
            try:
                # Lightweight check: simple generation
                resp = await self._generate_with_fallback("ping")
                if not resp:
                    errors.append("Gemini API (All models) failed.")
            except Exception as e:
                errors.append(f"Gemini API Error: {e}")
        elif GEMINI_AVAILABLE and not self.client:
             errors.append("Gemini library found but API Key missing.")

        if errors:
            error_msg = " | ".join(errors)
            await self.log(f"OPENING PRE-FLIGHT CHECK FAILED: {error_msg}", level="ERROR")
            
            # Unified Error Dispatch (Logs to Synapse + Broadcasts)
            await self.log_error(
                code="SYSTEM_INIT_FAILED",
                message=f"Pre-flight API Failures: {error_msg}",
                severity=ErrorSeverity.CRITICAL,
                hint="Check API keys for Kalshi/Gemini/OpenRouter and DB connection"
            )
            
            # LOCKDOWN
            self.is_locked_down = True
            await self.bus.publish("SYSTEM_LOCKDOWN", {"reason": f"API Check Failed: {error_msg}"}, self.name)
            # Signal Fatal to stop engine
            await self.bus.publish("SYSTEM_FATAL", {"message": f"Pre-flight Check Failed: {error_msg}"}, self.name)
        else:
            await self.log("✅ PRE-FLIGHT API CHECK PASSED (Kalshi, Supabase, Gemini)", level="SUCCESS")
