"""
MEGA-AGENT 3: THE BRAIN
Role: High-Level Decision Maker

Core BrainAgent class with debate, simulation, and monitoring capabilities.
"""
import asyncio
import os
import uuid
from typing import Any

from agents.base import BaseAgent
from core.ai_client import AIClient
from core.ai_utils import GEMINI_AVAILABLE, get_default_models, initialize_gemini_client
from core.bus import EventBus
from core.constants import (
    BRAIN_CONFIDENCE_THRESHOLD,
    BRAIN_MAX_VARIANCE,
    BRAIN_SIMULATION_ITERATIONS,
)
from core.db import log_to_db
from core.synapse import ExecutionSignal, MarketData, Opportunity, Synapse

from .debate import load_personas, run_debate
from .monitor import (
    check_opportunity_freshness,
    handle_restock_trigger,
    monitor_queue,
    process_single_item_from_queue,
)
from .simulation import run_simulation


class BrainAgent(BaseAgent):
    """The Decision Maker - Intelligence & Mathematical Verification"""

    CONFIDENCE_THRESHOLD = BRAIN_CONFIDENCE_THRESHOLD
    SIMULATION_ITERATIONS = BRAIN_SIMULATION_ITERATIONS
    MAX_VARIANCE = BRAIN_MAX_VARIANCE

    # Gemini model names to try (in order of preference)
    DEFAULT_MODELS = get_default_models()

    def __init__(self, agent_id: int, bus: EventBus, synapse: Synapse = None):
        super().__init__("BRAIN", agent_id, bus, synapse)
        self.execution_queue: list[dict] = []
        self.trading_instructions = ""

        # Flow control flags
        self.stop_requested = False
        self._is_monitoring = False
        self._monitoring_task = None
        self._dumped_count = 0
        self._last_restock_time = 0

        # Initialize Gemini
        self.gemini_model = None
        self._model_downgrade_warning = None  # Store for logging in async context
        self.client, self.ai_client, default_model, self._gemini_available = initialize_gemini_client(
            log_callback=self.log,
            bus=self.bus
        )

        # Try user-specified model first, then default list
        user_model = os.environ.get("GEMINI_MODEL")
        if user_model:
            # Defensive fix: 2.5 is deprecated/missing, downgrade to 2.0
            if "gemini-2.5" in user_model:
                self._model_downgrade_warning = f"Downgrading requested model {user_model} to gemini-2.0-flash-exp"
                self.gemini_model = "gemini-2.0-flash-exp"
            else:
                self.gemini_model = user_model
        else:
            self.gemini_model = default_model or self.DEFAULT_MODELS[0]

        # Load personas
        self.personas = load_personas()

    async def setup(self):
        ai_status = f"AI Model: {self.gemini_model}" if self.client else "AI: UNAVAILABLE (No API key)"
        await self.log(f"Brain online. Intelligence & Decision engine ready. {ai_status}")

        # Log any model downgrade warnings
        if self._model_downgrade_warning:
            await self.log(f"WARN: {self._model_downgrade_warning}", level="WARN")

        # Subscribe to control events only
        await self.bus.subscribe("INSTRUCTIONS_UPDATE", self.update_instructions)
        await self.bus.subscribe("SYSTEM_CONTROL", self.on_system_control)

        # Start the continuous monitoring loop
        self._monitoring_task = asyncio.create_task(self.monitor_queue())

    async def on_system_control(self, message):
        """Handle stop signals immediately"""
        action = message.payload.get("action")
        if action == "STOP_AUTOPILOT":
            self.stop_requested = True
            await self.log("Brain received STOP signal. Halting processing.")

    async def update_instructions(self, message):
        """Receive evolved instructions from Soul"""
        self.trading_instructions = message.payload.get("instructions", "")
        await self.log("Trading instructions updated from Soul.")

    async def monitor_queue(self):
        """CONTINUOUS MONITORING LOOP - delegates to monitor module"""
        await monitor_queue(
            brain_agent=self,
            stop_requested=self.stop_requested,
            synapse=self.synapse,
            log_callback=self.log,
            process_callback=self.process_single_item_from_queue
        )

    async def process_single_item_from_queue(self):
        """Process ONE opportunity from Synapse queue"""
        result = await process_single_item_from_queue(
            brain_agent=self,
            synapse=self.synapse,
            log_callback=self.log,
            process_opportunity_callback=self.process_single_opportunity,
            bus=self.bus,
            dumped_count=self._dumped_count,
            last_restock_time=self._last_restock_time
        )

        # Handle restock trigger
        if result in ("VETOED", "STALE", "SKIPPED"):
            self._dumped_count += 1

            should_reset, new_time = await handle_restock_trigger(
                result=result,
                dumped_count=self._dumped_count,
                last_restock_time=self._last_restock_time,
                synapse=self.synapse,
                bus=self.bus,
                log_callback=self.log
            )

            if should_reset:
                self._dumped_count = 0
            if new_time != self._last_restock_time:
                self._last_restock_time = new_time
        elif result == "APPROVED":
            self._dumped_count = 0

    async def run_intelligence(self, opp_queue: asyncio.Queue, exec_queue: asyncio.Queue):
        """Process opportunities from shared queue (Engine-driven)"""
        if not opp_queue.empty():
            opportunity = await opp_queue.get()
            await self.process_single_opportunity(opportunity)

    async def process_single_opportunity(self, opportunity: dict):
        """Core analysis logic"""
        ticker = opportunity.get("ticker", "UNKNOWN")

        # Check opportunity freshness
        is_fresh, freshness_status = check_opportunity_freshness(opportunity, self.log)
        if not is_fresh:
            return freshness_status

        await self.log(f"Analyzing: {ticker}")

        # 1. AI Debate (Optimist vs Critic) & Probability Estimation
        debate_result = await self.run_debate(opportunity)
        estimated_prob = debate_result.get("estimated_probability", 0.5)
        confidence = debate_result.get("confidence", 0)

        # FIX: Variance Veto Logic Bypass (Anti-Audit)
        if confidence == 0 or estimated_prob is None:
            reason = "Zero AI confidence" if confidence == 0 else "No probability estimate"
            await self.log(f"[VETO] VETOED: {ticker} | {reason} - skipping simulation", level="WARN")
            return "VETOED"

        # 2. Monte Carlo Simulation
        sim_result = self.run_simulation(opportunity, override_prob=estimated_prob)

        # 3. Decision
        variance = sim_result.get("variance", 1)
        ev = sim_result.get("ev", 0)

        # Only log and publish if we have valid data
        if variance == 999.0:
            await self.log(f"[SKIP] SKIPPED: {ticker} | No valid probability data available", level="DEBUG")
            return "SKIPPED"

        prob_str = f"{estimated_prob:.2f}" if estimated_prob is not None else "N/A"
        await self.log(f"AI Prob: {prob_str} | Conf: {confidence*100:.1f}% | EV: {ev:.3f}")

        # Publish simulation result for UI
        await self.bus.publish(
            "SIM_RESULT",
            {
                "ticker": ticker,
                "win_rate": float(sim_result.get("win_rate", 0.5)),
                "ev_score": float(ev),
                "variance": float(variance),
                "iterations": int(self.SIMULATION_ITERATIONS),
                "veto": bool(confidence < self.CONFIDENCE_THRESHOLD or variance > self.MAX_VARIANCE),
            },
            self.name,
        )

        if confidence >= self.CONFIDENCE_THRESHOLD and variance <= self.MAX_VARIANCE and ev > 0:
            await self.log(f"[OK] APPROVED: {ticker} | Pushing to execution.")
            await self.queue_for_execution(
                {
                    **opportunity,
                    "confidence": confidence,
                    "variance": variance,
                    "ev": ev,
                    "debate_reasoning": debate_result.get("reasoning", ""),
                }
            )
            return "APPROVED"

        reason = "Low confidence" if confidence < self.CONFIDENCE_THRESHOLD else ("High variance" if variance > self.MAX_VARIANCE else "Negative EV")
        await self.log(f"[X] VETOED: {ticker} | Reason: {reason}")
        return "VETOED"

    async def run_debate(self, opportunity: dict) -> dict:
        """Run multi-persona AI debate - delegates to debate module"""
        return await run_debate(
            opportunity=opportunity,
            client=self.client,
            gemini_model=self.gemini_model,
            personas=self.personas,
            trading_instructions=self.trading_instructions,
            ai_client=self.ai_client,
            log_callback=self.log,
            log_error_callback=self.log_error
        )

    def run_simulation(self, opportunity: dict, override_prob: float = None) -> dict:
        """Monte Carlo simulation - delegates to simulation module"""
        return run_simulation(
            opportunity=opportunity,
            override_prob=override_prob,
            simulation_iterations=self.SIMULATION_ITERATIONS
        )

    async def queue_for_execution(self, target: dict):
        """Push approved target to execution queue and Synapse"""
        execution_package = {
            "signal_id": str(uuid.uuid4()),
            "ticker": target.get("ticker", ""),
            "confidence": target.get("confidence", 0),
            "monte_carlo_ev": target.get("ev", 0),
            "reasoning": target.get("debate_reasoning", ""),
            "suggested_size": target.get("suggested_size", 0),
            "status": "READY_TO_STRIKE",
        }

        # 1. Synapse Integration
        if self.synapse:
            try:
                # Reconstruct Opportunity for the Signal
                m_data_raw = target.get("market_data", {})
                m_data = MarketData(
                    ticker=target.get("ticker", ""),
                    title=m_data_raw.get("title", ""),
                    subtitle=m_data_raw.get("subtitle", ""),
                    yes_price=int(target.get("kalshi_price", 0.5) * 100),
                    no_price=m_data_raw.get("no_price", 0),
                    volume=int(m_data_raw.get("volume", 0)),
                    expiration=m_data_raw.get("expiration_time", ""),
                    raw_response=m_data_raw
                )

                opp = Opportunity(
                    id=target.get("id", str(uuid.uuid4())),
                    ticker=target.get("ticker", ""),
                    market_data=m_data
                )

                signal_model = ExecutionSignal(
                    id=execution_package["signal_id"],
                    target_opportunity=opp,
                    confidence=execution_package["confidence"],
                    monte_carlo_ev=execution_package["monte_carlo_ev"],
                    reasoning=execution_package["reasoning"],
                    suggested_count=execution_package["suggested_size"] or 10,
                    status="PENDING"
                )

                await self.synapse.executions.push(signal_model)
                await self.log(f"Synapse Push (EXECUTION): {target['ticker']}")
            except Exception as e:
                await self.log(f"Synapse Execution Push Failed: {e}", level="ERROR")

        # 2. Legacy Flow (Keep for Hand compatibility)
        self.execution_queue.append(target)
        await log_to_db("execution_queue", execution_package)
        await self.bus.publish(
            "EXECUTION_READY",
            {
                "ticker": target.get("ticker", ""),
                "signal_id": execution_package["signal_id"],
                "confidence": execution_package["confidence"],
                "ev": execution_package["monte_carlo_ev"],
            },
            self.name,
        )

    def pop_execution_target(self) -> dict | None:
        """Get next target for Hand to execute"""
        return self.execution_queue.pop(0) if self.execution_queue else None

    async def on_tick(self, payload: dict[str, Any]):
        pass  # Brain is event-driven
