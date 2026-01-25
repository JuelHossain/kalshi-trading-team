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
import os
import uuid
from typing import Any

import numpy as np
from agents.base import BaseAgent
from core.bus import EventBus
from core.db import log_to_db

try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


from core.synapse import Synapse, ExecutionSignal, Opportunity, MarketData


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
        else:
            self.client = None

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
        
        # 1. Synapse Flow (Persistent Queue)
        if self.synapse:
            try:
                opp_model = await self.synapse.opportunities.pop()
                if opp_model:
                    await self.log(f"🧠 Synapse Input: {opp_model.ticker}")
                    
                    # Map Pydantic Model -> Legacy Dict for compatibility
                    opp_dict = opp_model.model_dump()
                    
                    # Fix Price: Model has int (50), Brain logic expects float (0.50)
                    kalshi_cents = opp_model.market_data.yes_price
                    opp_dict["kalshi_price"] = kalshi_cents / 100.0
                    
                    # Ensure flattened structure matches expectations
                    opp_dict["market_data"] = opp_model.market_data.model_dump()
                    
                    await self.process_single_opportunity(opp_dict)
                    return # Process one at a time per event
                    
            except Exception as e:
                await self.log(f"Synapse Pop Error: {e}", level="ERROR")

        # 2. Legacy Flow (Direct Senses Link)
        if not self.senses:
            return

        opportunity = self.senses.pop_opportunity()
        if opportunity:
            await self.process_single_opportunity(opportunity)

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

        await self.log(f"AI Prob: {estimated_prob:.2f} | Conf: {confidence*100:.1f}% | EV: {ev:.3f}")

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
            await self.log(f"✅ APPROVED: {ticker} | Pushing to execution.")
            await self.queue_for_execution(
                {
                    **opportunity,
                    "confidence": confidence,
                    "variance": variance,
                    "ev": ev,
                    "debate_reasoning": debate_result.get("reasoning", ""),
                }
            )
        else:
            reason = "Low confidence" if confidence < self.CONFIDENCE_THRESHOLD else ("High variance" if variance > self.MAX_VARIANCE else "Negative EV")
            await self.log(f"❌ VETOED: {ticker} | Reason: {reason}")

    async def run_debate(self, opportunity: dict) -> dict:
        """Multi-persona AI debate using Gemini"""
        if not self.client:
            await self.log("Gemini unavailable. Using heuristic confidence.")
            return {
                "confidence": 0.5,
                "reasoning": "Heuristic only",
                "estimated_probability": 0.5
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
OPTIMIST: Argue why this is a great opportunity.
CRITIC: Argue against this trade.
JUDGE: Final verdict.

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
            import json
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
        except Exception as e:
            await self.log(f"Debate error: {str(e)[:50]}", level="ERROR")

        return {"confidence": 0.5, "reasoning": "Debate failed", "estimated_probability": 0.5}

    def run_simulation(self, opportunity: dict, override_prob: float = None) -> dict:
        """Monte Carlo simulation for variance and EV calculation"""
        # Use overridden probability (AI estimate) if available, else default
        vegas_prob = override_prob if override_prob is not None else opportunity.get("vegas_prob", 0.5)
        if vegas_prob is None: vegas_prob = 0.5
        
        kalshi_price = opportunity.get("kalshi_price", 0.5)

        # Simulate outcomes
        np.random.seed(42)  # Reproducibility
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
