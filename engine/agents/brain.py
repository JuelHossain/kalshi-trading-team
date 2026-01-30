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
from typing import Any

import numpy as np
from agents.base import BaseAgent
from core.bus import EventBus
from core.db import log_to_db
from core.error_dispatcher import ErrorSeverity

try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


from core.synapse import Synapse, ExecutionSignal, Opportunity, MarketData


def safe_log(message: str, level: str = "INFO"):
    """Windows-safe logging that removes emojis."""
    import re
    # Remove emojis for Windows console compatibility
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        "]+", flags=re.UNICODE)
    clean_message = emoji_pattern.sub(r'', message)
    print(f"[{level}] {clean_message}")


class BrainAgent(BaseAgent):
    """The Decision Maker - Intelligence & Mathematical Verification"""

    CONFIDENCE_THRESHOLD = 0.85  # 85% minimum confidence
    SIMULATION_ITERATIONS = 10000
    MAX_VARIANCE = 0.25  # Maximum acceptable variance

    def __init__(self, agent_id: int, bus: EventBus, senses_agent=None, synapse: Synapse = None):
        super().__init__("BRAIN", agent_id, bus, synapse)
        self.senses = senses_agent
        self.execution_queue: list[dict] = []
        self.trading_instructions = ""

        # Initialize Gemini
        if GEMINI_AVAILABLE:
            api_key = os.environ.get("GEMINI_API_KEY")
            if api_key:
                self.client = genai.Client(api_key=api_key)
            else:
                self.client = None
        
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
                with open(opt_path, "r") as f:
                    self.personas["optimist"] = f"OPTIMIST: {f.read().strip()}"

            if os.path.exists(cri_path):
                with open(cri_path, "r") as f:
                    self.personas["critic"] = f"CRITIC: {f.read().strip()}"

        except Exception as e:
            print(f"[BRAIN] Persona Load Warning: {e}")
            # Continue with default personas
            pass

    async def setup(self):
        await self.log("Brain online. Intelligence & Decision engine ready.")
        await self.bus.subscribe("OPPORTUNITIES_READY", self.process_opportunities)
        await self.bus.subscribe("INSTRUCTIONS_UPDATE", self.update_instructions)

    async def update_instructions(self, message):
        """Receive evolved instructions from Soul"""
        self.trading_instructions = message.payload.get("instructions", "")
        await self.log("Trading instructions updated from Soul.")

    async def process_opportunities(self, message):
        """Process queued opportunities > Synapse (Primary) or Senses (Legacy)"""

        # Track decision statistics
        approved_count = 0
        vetoed_count = 0
        skipped_count = 0

        # 1. Synapse Flow (Persistent Queue)
        if self.synapse:
            try:
                queue_size = await self.synapse.opportunities.size()
                await self.log(f"Synapse Queue Size: {queue_size} opportunities to process")

                # Process ALL opportunities in the queue, not just one
                processed_count = 0
                while True:
                    opp_model = await self.synapse.opportunities.pop()
                    if not opp_model:
                        # Queue is empty
                        break

                    safe_log(f"Synapse Input: {opp_model.ticker}")

                    # Map Pydantic Model -> Legacy Dict for compatibility
                    opp_dict = opp_model.model_dump()

                    # Fix Price: Model has int (50), Brain logic expects float (0.50)
                    kalshi_cents = opp_model.market_data.yes_price
                    opp_dict["kalshi_price"] = kalshi_cents / 100.0

                    # Ensure flattened structure matches expectations
                    opp_dict["market_data"] = opp_model.market_data.model_dump()

                    # Track decision
                    result = await self.process_single_opportunity(opp_dict)
                    processed_count += 1

                    if result == "APPROVED":
                        approved_count += 1
                    elif result == "VETOED":
                        vetoed_count += 1
                    elif result == "SKIPPED":
                        skipped_count += 1

                # Log summary of decisions
                await self.log(f"Synapse Processing Complete: {processed_count} analyzed | [OK] {approved_count} approved | [VETO] {vetoed_count} vetoed | [SKIP] {skipped_count} skipped")

            except Exception as e:
                await self.log(f"Synapse Pop Error: {e}", level="ERROR")

        # 2. Legacy Flow (Direct Senses Link) - DEPRECATED
        if not self.senses:
            return

        # Process legacy queue until empty
        processed_legacy = 0
        while True:
            opportunity = self.senses.pop_opportunity()
            if not opportunity:
                break
            result = await self.process_single_opportunity(opportunity)
            processed_legacy += 1
            if result == "APPROVED":
                approved_count += 1
            elif result == "VETOED":
                vetoed_count += 1

        if processed_legacy > 0:
            await self.log(f"Legacy Queue Processed: {processed_legacy} opportunities")

    async def run_intelligence(self, opp_queue: asyncio.Queue, exec_queue: asyncio.Queue):
        """Process opportunities from shared queue (Engine-driven)"""
        if not opp_queue.empty():
            opportunity = await opp_queue.get()
            await self.process_single_opportunity(opportunity)

    async def process_single_opportunity(self, opportunity: dict):
        """Core analysis logic"""
        ticker = opportunity.get("ticker", "UNKNOWN")
        await self.log(f"Analyzing: {ticker}")

        # 1. AI Debate (Optimist vs Critic) & Probability Estimation
        debate_result = await self.run_debate(opportunity)
        estimated_prob = debate_result.get("estimated_probability", 0.5)

        # 2. Monte Carlo Simulation
        sim_result = self.run_simulation(opportunity, override_prob=estimated_prob)

        # 3. Decision
        confidence = debate_result.get("confidence", 0)
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
        await self.bus.publish(
            "SIM_RESULT",
            {
                "ticker": ticker,
                "win_rate": sim_result.get("win_rate", 0.5),
                "ev_score": ev,
                "variance": variance,
                "iterations": self.SIMULATION_ITERATIONS,
                "veto": confidence < self.CONFIDENCE_THRESHOLD or variance > self.MAX_VARIANCE,
            },
            self.name,
        )

        if confidence >= self.CONFIDENCE_THRESHOLD and variance <= self.MAX_VARIANCE and ev > 0:
            safe_log(f"[OK] APPROVED: {ticker} | Pushing to execution.")
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
        else:
            reason = "Low confidence" if confidence < self.CONFIDENCE_THRESHOLD else ("High variance" if variance > self.MAX_VARIANCE else "Negative EV")
            safe_log(f"[X] VETOED: {ticker} | Reason: {reason}")
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
            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.client.models.generate_content(model="gemini-1.5-pro", contents=prompt)
            )

            # Parse response
            text = response.text
            import re

            # Extract JSON from response
            json_match = re.search(r"\{.*\}", text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return {
                    "confidence": result.get("confidence", 50) / 100,
                    "reasoning": result.get("judge_verdict", ""),
                    "estimated_probability": result.get("estimated_probability", 0.5)
                }
            else:
                await self.log_error(
                    code="INTELLIGENCE_PARSE_ERROR",
                    message="No JSON found in AI response",
                    severity=ErrorSeverity.HIGH,
                    context={"ticker": ticker}
                )
                # Return zero confidence to trigger veto
                return {"confidence": 0.0, "reasoning": "Invalid AI response format - trade rejected", "estimated_probability": None}

        except json.JSONDecodeError as e:
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
            # Return zero confidence to trigger veto
            return {"confidence": 0.0, "reasoning": "AI service unavailable - trade rejected", "estimated_probability": None}

        except Exception as e:
            # Catch-all for unexpected errors - log full details for debugging
            error_type = type(e).__name__
            await self.log_error(
                code="INTELLIGENCE_DEBATE_FAILED",
                message=f"Debate error ({error_type}) for {ticker}",
                severity=ErrorSeverity.HIGH,
                context={"ticker": ticker, "error_type": error_type, "error": str(e)[:100]},
                exception=e
            )
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

        return {"win_rate": win_rate, "ev": ev, "variance": variance}

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
