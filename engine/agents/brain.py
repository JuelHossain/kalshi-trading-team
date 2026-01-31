"""
MEGA-AGENT 3: THE BRAIN
Role: High-Level Decision Maker

Workflow:
1. Queue Watcher: Pull top-ranked match from Opportunity Queue
2. The Debate: Gemini 1.5 Pro multi-persona debate (Optimist vs Critic)
3. Simulation: 10,000-iteration numpy simulation for variance check
4. The Result: If Confidence > 85%, push to Execution Queue
"""

import asyncio
import json
import os
import uuid
from datetime import datetime
from typing import Any

import aiohttp
import numpy as np
from agents.base import BaseAgent
from core.ai_client import AIClient
from core.bus import EventBus
from core.constants import BRAIN_CONFIDENCE_THRESHOLD, BRAIN_SIMULATION_ITERATIONS, BRAIN_MAX_VARIANCE
from core.db import log_to_db
from core.error_dispatcher import ErrorSeverity
from core.flow_control import check_execution_queue_limit, should_restock
from core.logger import get_logger

try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


from core.synapse import ExecutionSignal, MarketData, Opportunity, Synapse


class BrainAgent(BaseAgent):
    """The Decision Maker - Intelligence & Mathematical Verification"""

    CONFIDENCE_THRESHOLD = BRAIN_CONFIDENCE_THRESHOLD
    SIMULATION_ITERATIONS = BRAIN_SIMULATION_ITERATIONS
    MAX_VARIANCE = BRAIN_MAX_VARIANCE  # Maximum acceptable variance

    # Gemini model names to try (in order of preference)
    # Can be overridden via GEMINI_MODEL env var
    DEFAULT_MODELS = [
        "gemini-3-flash-preview",
        "gemini-3-pro-preview",
        "gemini-2.0-flash-thinking-exp-01-21",
        "gemini-2.0-pro-exp-02-05",
        "gemini-2.0-flash-exp",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
    ]

    def __init__(self, agent_id: int, bus: EventBus, synapse: Synapse = None):
        super().__init__("BRAIN", agent_id, bus, synapse)
        # self.senses = senses_agent  # Removed direct reference
        self.execution_queue: list[dict] = []
        self.trading_instructions = ""

        # Flow control flags
        self.stop_requested = False
        self._is_monitoring = False
        self._monitoring_task = None
        self._dumped_count = 0  # Track vetoes for restock trigger
        self._last_restock_time = 0  # Unix timestamp for cooldown

        # Initialize Gemini
        self.gemini_model = None
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
                # Try user-specified model first, then default list
                user_model = os.environ.get("GEMINI_MODEL")
                if user_model:
                    # Defensive fix: 2.5 is deprecated/missing, downgrade to 2.0
                    if "gemini-2.5" in user_model:
                        get_logger("BRAIN").warning(f"[BRAIN] WARN: Downgrading requested model {user_model} to gemini-2.0-flash-exp")
                        self.gemini_model = "gemini-2.0-flash-exp"
                    else:
                        self.gemini_model = user_model
                else:
                    self.gemini_model = self.DEFAULT_MODELS[0]
            else:
                self.client = None
                self.gemini_model = None
                self.ai_client = None
        
        # OpenCode Personas
        self.personas = {
            "optimist": "OPTIMIST: Argue why this is a great opportunity.",
            "critic": "CRITIC: Argue against this trade."
        }
        self.load_personas()

    def load_personas(self):
        """Load character definitions from the centralized ai-env library"""
        base_path = "ai-env/personas"
        try:
            opt_path = os.path.join(base_path, "optimist.md")
            cri_path = os.path.join(base_path, "critic.md")

            if os.path.exists(opt_path):
                with open(opt_path) as f:
                    self.personas["optimist"] = f"OPTIMIST: {f.read().strip()}"

            if os.path.exists(cri_path):
                with open(cri_path) as f:
                    self.personas["critic"] = f"CRITIC: {f.read().strip()}"

        except Exception as e:
            get_logger("BRAIN").warning(f"[BRAIN] Persona Load Warning: {e}")
            # Continue with default personas

    async def setup(self):
        ai_status = f"AI Model: {self.gemini_model}" if self.client else "AI: UNAVAILABLE (No API key)"
        await self.log(f"Brain online. Intelligence & Decision engine ready. {ai_status}")
        # Subscribe to control events only - NOT OPPORTUNITIES_READY
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
        """CONTINUOUS MONITORING LOOP
        Checks Synapse opportunity queue and processes ALL items until empty.
        When empty, waits for new items to appear.

        This is the MAIN Brain processing loop - runs continuously."""
        await self.log("Starting continuous queue monitoring loop...", level="DEBUG")

        while not self.stop_requested:
            try:
                # Check if Synapse exists
                if not self.synapse:
                    await asyncio.sleep(1)
                    continue

                # FLOW CONTROL: Check if execution queue is at limit
                is_at_limit, exec_size = await check_execution_queue_limit(self.synapse)
                if is_at_limit:
                    await self.log(f"Flow Control: Execution queue at limit ({exec_size}/10). Pausing analysis.", level="WARN")
                    await asyncio.sleep(2)
                    continue

                # Check queue size
                queue_size = await self.synapse.opportunities.size()

                if queue_size == 0:
                    # No opportunities - wait before checking again
                    await asyncio.sleep(1)
                    continue

                # Process ALL opportunities in queue until empty
                await self.log(f"Found {queue_size} opportunities. Processing batch...", level="INFO")

                while queue_size > 0 and not self.stop_requested:
                    # Check execution queue limit before each item
                    is_at_limit, exec_size = await check_execution_queue_limit(self.synapse)
                    if is_at_limit:
                        await self.log(f"Flow Control: Execution queue at limit ({exec_size}/10). Stopping batch.", level="WARN")
                        break

                    # Process ONE opportunity
                    await self.process_single_item_from_queue()

                    # Small delay between items
                    await asyncio.sleep(0.5)

                    # Update queue size
                    queue_size = await self.synapse.opportunities.size()

                if queue_size == 0:
                    await self.log("Batch complete. All opportunities processed.", level="SUCCESS")
                else:
                    await self.log(f"Batch stopped. {queue_size} opportunities remaining.", level="DEBUG")

            except Exception as e:
                await self.log(f"Monitor loop error: {str(e)[:100]}", level="ERROR")
                await asyncio.sleep(2)  # Wait before retrying

        await self.log("Monitoring loop stopped.", level="INFO")

    async def process_single_item_from_queue(self):
        """Process ONE opportunity from Synapse queue
        Analyzes it and decides to:
        - Push to Execution Queue (if valuable)
        - Dump/veto (if not valuable)"""

        # Pop one opportunity from queue
        opp_model = await self.synapse.opportunities.pop()
        if not opp_model:
            return  # Queue was empty

        await self.log(f"Synapse Input: {opp_model.ticker}")

        # Map Pydantic Model -> Legacy Dict for compatibility
        opp_dict = opp_model.model_dump()

        # Fix Price: Model has int (50), Brain logic expects float (0.50)
        kalshi_cents = opp_model.market_data.yes_price
        opp_dict["kalshi_price"] = kalshi_cents / 100.0

        # Ensure flattened structure matches expectations
        opp_dict["market_data"] = opp_model.market_data.model_dump()

        # Track decision
        result = await self.process_single_opportunity(opp_dict)

        # Track dumped count for restock trigger
        if result in ("VETOED", "STALE", "SKIPPED"):
            self._dumped_count += 1

            # When 5 opportunities dumped, request restock from Senses
            if self._dumped_count >= 5:
                import time
                now = time.time()

                # Check if we should restock using centralized flow control
                should_request = await should_restock(
                    self.synapse,
                    self._dumped_count,
                    self._last_restock_time,
                    now
                )

                if should_request:
                    await self.log(f"Dumped {self._dumped_count} opportunities. Requesting restock from Senses...")
                    await self.bus.publish("REQUEST_RESTOCK", {}, self.name)
                    self._last_restock_time = now
                elif exec_size >= 10:
                    await self.log(f"Flow Control: Execution queue at limit ({exec_size}/10). NOT requesting restock.", level="WARN")
                else:
                    cooldown = 60  # 60 seconds cooldown
                    await self.log(f"Flow Control: Restock cooldown active ({cooldown - (now - self._last_restock_time):.0f}s remaining).", level="DEBUG")

                self._dumped_count = 0  # Reset counter
        elif result == "APPROVED":
            # Reset dumped counter on approval
            self._dumped_count = 0

    async def run_intelligence(self, opp_queue: asyncio.Queue, exec_queue: asyncio.Queue):
        """Process opportunities from shared queue (Engine-driven)"""
        if not opp_queue.empty():
            opportunity = await opp_queue.get()
            await self.process_single_opportunity(opportunity)

    async def process_single_opportunity(self, opportunity: dict):
        """Core analysis logic"""
        ticker = opportunity.get("ticker", "UNKNOWN")
        
        # --- HARDENING: Opportunity TTL Check (Anti-Stale) ---
        # Requirement: Reject opportunities older than 60 seconds
        now = datetime.now()
        ts = opportunity.get("timestamp")
        
        # Handle both datetime objects and ISO strings
        if isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts)
            except ValueError:
                ts = None
        
        if ts:
            age = (now - ts).total_seconds()
            if age >= 60:  # Use >= to handle boundary case of exactly 60 seconds
                await self.log(f"[STALE] Opportunity expired: {ticker} (Age: {age:.0f}s) - skipping", level="WARN")
                return "STALE"
        else:
            # For safety, if no timestamp exists, treat as potentially stale
            await self.log(f"[STALE] Opportunity has no timestamp: {ticker} - skipping for safety", level="WARN")
            return "STALE"

        await self.log(f"Analyzing: {ticker}")

        # 1. AI Debate (Optimist vs Critic) & Probability Estimation
        debate_result = await self.run_debate(opportunity)
        estimated_prob = debate_result.get("estimated_probability", 0.5)
        confidence = debate_result.get("confidence", 0)

        # FIX: Variance Veto Logic Bypass (Anti-Audit)
        # Early veto if AI failed (zero confidence or no probability estimate)
        # This prevents wasteful Monte Carlo simulation when result is predetermined
        if confidence == 0 or estimated_prob is None:
            reason = "Zero AI confidence" if confidence == 0 else "No probability estimate"
            await self.log(f"[VETO] VETOED: {ticker} | {reason} - skipping simulation", level="WARN")
            return "VETOED"

        # 2. Monte Carlo Simulation
        sim_result = self.run_simulation(opportunity, override_prob=estimated_prob)

        # 3. Decision
        variance = sim_result.get("variance", 1)
        ev = sim_result.get("ev", 0)

        # Only log and publish if we have valid data (variance 999 indicates no valid probability)
        if variance == 999.0:
            # Skip processing opportunities with no valid probability data
            await self.log(f"[SKIP] SKIPPED: {ticker} | No valid probability data available", level="DEBUG")
            return "SKIPPED"

        prob_str = f"{estimated_prob:.2f}" if estimated_prob is not None else "N/A"
        await self.log(f"AI Prob: {prob_str} | Conf: {confidence*100:.1f}% | EV: {ev:.3f}")

        # Publish simulation result for UI
        await self.log(f"[DEBUG] Publishing SIM_RESULT for {ticker}...", level="DEBUG")
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
        await self.log(f"[DEBUG] SIM_RESULT published for {ticker}", level="DEBUG")
        await self.log(f"[DEBUG] Checking decision: conf={confidence:.2f}, thresh={self.CONFIDENCE_THRESHOLD}, var={variance:.2f}, max_var={self.MAX_VARIANCE}, ev={ev:.3f}", level="DEBUG")

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
        """Multi-persona AI debate using Gemini"""
        if not self.client:
            # Use centralized error system
            await self.log_error(
                code="INTELLIGENCE_AI_UNAVAILABLE",
                severity=ErrorSeverity.HIGH,
                context={"opportunity": opportunity.get("ticker", "UNKNOWN")}
            )
            # Return zero confidence to trigger veto
            return {
                "confidence": 0.0,  # Force veto
                "reasoning": "AI service unavailable - trade rejected for safety",
                "estimated_probability": None  # No fallback estimation
            }

        ticker = opportunity.get("ticker", "UNKNOWN")
        market_data = opportunity.get("market_data", {})
        title = market_data.get("title", ticker)
        subtitle = market_data.get("subtitle", "")
        
        kalshi_price = opportunity.get("kalshi_price", 0.5)
        
        # Check if we have external odds (legacy support)
        has_odds = opportunity.get("vegas_prob") is not None
        odds_context = f"Vegas Probability: {opportunity['vegas_prob']*100:.1f}%" if has_odds else "NO EXTERNAL ODDS AVAILABLE."
        
        fetched_news = opportunity.get("external_context", "")
        full_context = f"ODDS: {odds_context}\nNEWS/CONTEXT:\n{fetched_news}" if fetched_news else f"ODDS: {odds_context}\n(No news found)"

        prompt = f"""You are a trading committee with two personas debating a market opportunity.

MARKET: {ticker}
TITLE: {title}
SUBTITLE: {subtitle}
Current Kalshi Price: {kalshi_price*100:.1f}%
Context: {full_context}

{f"Today's Trading Instructions: {self.trading_instructions[:500]}" if self.trading_instructions else ""}

TASK:
1. Estimate the TRUE probability of this event occurring (0.00 to 1.00) based on your knowledge of the world and the provided Context.
2. Debate the trade at the current price.
3. Explicitly reference the 'NEWS/CONTEXT' in your reasoning if available.

PERSONAS:
{self.personas['optimist']}

{self.personas['critic']}

JUDGE: Final verdict based on the debate above.

Respond in JSON format:
{{
  "optimist": "...",
  "critic": "...",
  "judge_verdict": "...",
  "estimated_probability": 0.75,
  "confidence": 85
}}"""

        try:
            try:
                # Primary: Google Gemini API
                response = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: self.client.models.generate_content(model=self.gemini_model, contents=prompt)
                )
                text = response.text
            except Exception as e:
                # Fallback: OpenRouter
                await self.log(f"[BRAIN] Primary AI failed ({str(e)[:50]})... Attempting OpenRouter Fallback.", level="WARN")
                text = await self.ai_client._call_openrouter(prompt) if self.ai_client else None
                if not text:
                    raise e # Re-raise if fallback failed

            # Parse response
            # text is already set above
            import re

            # Extract JSON from response
            # Try multiple patterns to find JSON
            json_match = re.search(r"\{.*\}", text, re.DOTALL)
            if json_match:
                try:
                    result = json.loads(json_match.group())
                    return {
                        "confidence": result.get("confidence", 50) / 100,
                        "reasoning": result.get("judge_verdict", ""),
                        "estimated_probability": result.get("estimated_probability", 0.5)
                    }
                except json.JSONDecodeError as je:
                    # Log the actual response for debugging
                    await self.log(f"JSON parse error for {ticker}. Response: {text[:200]}", level="ERROR")
                    await self.log_error(
                        code="INTELLIGENCE_PARSE_ERROR",
                        message=f"JSON parsing failed for {ticker}",
                        severity=ErrorSeverity.HIGH,
                        context={"ticker": ticker, "error": str(je)[:100], "response_preview": text[:200]},
                        exception=je
                    )
                    # Return zero confidence to trigger veto
                    return {"confidence": 0.0, "reasoning": f"JSON parse error - trade rejected: {str(je)[:50]}", "estimated_probability": None}

            # No JSON found at all
            await self.log(f"No JSON found in AI response for {ticker}. Response: {text[:200]}", level="ERROR")
            await self.log_error(
                code="INTELLIGENCE_PARSE_ERROR",
                message="No JSON found in AI response",
                severity=ErrorSeverity.HIGH,
                context={"ticker": ticker, "response_preview": text[:200]}
            )
            # Return zero confidence to trigger veto
            return {"confidence": 0.0, "reasoning": "Invalid AI response format - trade rejected", "estimated_probability": None}

        except json.JSONDecodeError as e:
            # Log with more context
            await self.log(f"JSON decode error for {ticker}: {str(e)[:100]}", level="ERROR")
            await self.log_error(
                code="INTELLIGENCE_PARSE_ERROR",
                message=f"JSON parsing failed for {ticker}",
                severity=ErrorSeverity.HIGH,
                context={"ticker": ticker, "error": str(e)[:100]},
                exception=e
            )
            # Return zero confidence to trigger veto
            return {"confidence": 0.0, "reasoning": f"JSON parse error - trade rejected: {str(e)[:50]}", "estimated_probability": None}

        except AttributeError as e:
            await self.log_error(
                code="INTELLIGENCE_PARSE_ERROR",
                message="AI response format error",
                severity=ErrorSeverity.HIGH,
                context={"ticker": ticker, "error": str(e)[:100]},
                exception=e
            )
            # Return zero confidence to trigger veto
            return {"confidence": 0.0, "reasoning": f"Invalid AI response format - trade rejected: {str(e)[:50]}", "estimated_probability": None}

        except ConnectionError as e:
            await self.log_error(
                code="INTELLIGENCE_TIMEOUT",
                message="AI API connection failed",
                severity=ErrorSeverity.HIGH,
                context={"ticker": ticker, "error": str(e)[:100]},
                exception=e
            )
            await asyncio.sleep(0.5) # Prevent rapid retries
            # Return zero confidence to trigger veto
            return {"confidence": 0.0, "reasoning": "AI service unavailable - trade rejected", "estimated_probability": None}

        except Exception as e: # Handle ClientError and others
            # Catch-all for unexpected errors - log full details for debugging
            error_type = type(e).__name__
            await self.log_error(
                code="INTELLIGENCE_DEBATE_FAILED",
                message=f"Debate error ({error_type}) for {ticker}",
                severity=ErrorSeverity.HIGH,
                context={"ticker": ticker, "error_type": error_type, "error": str(e)[:100]},
                exception=e
            )
            await asyncio.sleep(0.5) # Prevent rapid retries
            # Return zero confidence to trigger veto
            return {"confidence": 0.0, "reasoning": f"Debate failed ({error_type}) - trade rejected", "estimated_probability": None}

    def run_simulation(self, opportunity: dict, override_prob: float = None) -> dict:
        """Monte Carlo simulation for variance and EV calculation"""
        # Use overridden probability (AI estimate) if available
        vegas_prob = override_prob if override_prob is not None else opportunity.get("vegas_prob")

        # If no valid probability available, return failure state
        if vegas_prob is None:
            return {
                "win_rate": 0.0,
                "ev": -999.0,  # Highly negative EV to force veto
                "variance": 999.0  # High variance to force veto
            }

        kalshi_price = opportunity.get("kalshi_price", 0.5)

        # Simulate outcomes
        # Only use fixed seed for debugging/testing (set SIMULATION_USE_FIXED_SEED=true in .env)
        # Production simulations should be truly random for accurate variance estimation
        if os.getenv("SIMULATION_USE_FIXED_SEED") == "true":
            np.random.seed(42)
        outcomes = np.random.binomial(1, vegas_prob, self.SIMULATION_ITERATIONS)

        # Calculate returns per simulation
        # Win: (1 - kalshi_price) profit | Lose: kalshi_price loss
        returns = np.where(outcomes == 1, (1 - kalshi_price), -kalshi_price)

        win_rate = outcomes.mean()
        ev = returns.mean()
        variance = returns.var()

        return {"win_rate": float(win_rate), "ev": float(ev), "variance": float(variance)}

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

        # 2. Legacy Flow (Keep for Hand compatibility until Hand is refactored)
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
