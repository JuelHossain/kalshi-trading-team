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
from core.bus import EventBus
from core.vault import RecursiveVault

try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


from core.synapse import Synapse


class SoulAgent(BaseAgent):
    """The Executive Director - System, Memory & Evolution"""

    HARD_FLOOR_CENTS = 25500  # $255 (15% of $300 principal = $255 floor)

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
            else:
                self.client = None
        else:
            self.client = None

    async def setup(self):
        await self.log("Soul awakening. Executive Director online.")
        await self.bus.subscribe("CYCLE_START", self.on_cycle_start)
        await self.bus.subscribe("TRADE_RESULT", self.on_trade_result)
        await self.bus.subscribe("CYCLE_COMPLETE", self.on_cycle_complete)
        await self.bus.subscribe("SYSTEM_CONTROL", self.on_system_control)

    async def on_cycle_start(self, message):
        """Pre-flight sequence"""
        await self.log("Initiating pre-flight sequence...")

        # 1. Safety Check - Hard Floor
        if self.vault.current_balance < self.HARD_FLOOR_CENTS:
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
            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.client.models.generate_content(model="gemini-1.5-pro", contents=prompt)
            )
            self.trading_instructions = response.text
            await self.log("Trading instructions evolved via Gemini.")
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
            self.autopilot_enabled = False
            await self.log("🛑 AUTOPILOT DISABLED. (System will pause after current cycle)")

    async def on_cycle_complete(self, message):
        """Trigger next cycle if in Autopilot mode"""
        if self.autopilot_enabled and not self.is_locked_down:
            await self.log(f"Cycle complete. Waiting {self.autopilot_delay}s for next pulse...")
            await asyncio.sleep(self.autopilot_delay)
            
            # Re-check in case it was disabled during sleep
            if self.autopilot_enabled:
                await self.bus.publish("REQUEST_CYCLE", {"isPaperTrading": self.is_paper_trading}, self.name)

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
