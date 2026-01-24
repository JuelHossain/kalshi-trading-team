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
import numpy as np
from datetime import datetime
from typing import Dict, Any, Optional, List
from agents.base import BaseAgent
from core.bus import EventBus
from core.db import log_to_db
import uuid

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


class BrainAgent(BaseAgent):
    """The Decision Maker - Intelligence & Mathematical Verification"""
    
    CONFIDENCE_THRESHOLD = 0.85  # 85% minimum confidence
    SIMULATION_ITERATIONS = 10000
    MAX_VARIANCE = 0.25  # Maximum acceptable variance
    
    def __init__(self, agent_id: int, bus: EventBus, senses_agent=None):
        super().__init__("BRAIN", agent_id, bus)
        self.senses = senses_agent
        self.execution_queue: List[Dict] = []
        self.trading_instructions = ""
        
        # Initialize Gemini
        if GEMINI_AVAILABLE:
            api_key = os.environ.get("GEMINI_API_KEY")
            if api_key:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel('gemini-1.5-pro')
            else:
                self.model = None
        else:
            self.model = None

    async def setup(self):
        await self.log("Brain online. Intelligence & Decision engine ready.")
        await self.bus.subscribe("OPPORTUNITIES_READY", self.process_opportunities)
        await self.bus.subscribe("INSTRUCTIONS_UPDATE", self.update_instructions)

    async def update_instructions(self, message):
        """Receive evolved instructions from Soul"""
        self.trading_instructions = message.payload.get("instructions", "")
        await self.log("Trading instructions updated from Soul.")

    async def process_opportunities(self, message):
        """Process queued opportunities through AI debate and simulation"""
        await self.log("Opportunities received. Initiating analysis...")
        
        # Get top opportunity from Senses
        if not self.senses:
            await self.log("Senses agent not connected. Cannot process.", level="ERROR")
            return
            
        opportunity = self.senses.pop_opportunity()
        if not opportunity:
            await self.log("No opportunities to process.")
            return
        
        ticker = opportunity.get('ticker', 'UNKNOWN')
        await self.log(f"Analyzing: {ticker}")
        
        # 1. AI Debate (Optimist vs Critic)
        debate_result = await self.run_debate(opportunity)
        
        # 2. Monte Carlo Simulation
        sim_result = self.run_simulation(opportunity)
        
        # 3. Decision
        confidence = debate_result.get('confidence', 0)
        variance = sim_result.get('variance', 1)
        
        await self.log(f"Debate confidence: {confidence*100:.1f}% | Sim variance: {variance:.3f}")
        
        # Publish simulation result for UI
        await self.bus.publish("SIM_RESULT", {
            "ticker": ticker,
            "win_rate": sim_result.get('win_rate', 0.5),
            "ev_score": sim_result.get('ev', 0),
            "variance": variance,
            "iterations": self.SIMULATION_ITERATIONS,
            "veto": confidence < self.CONFIDENCE_THRESHOLD or variance > self.MAX_VARIANCE
        }, self.name)
        
        if confidence >= self.CONFIDENCE_THRESHOLD and variance <= self.MAX_VARIANCE:
            await self.log(f"✅ APPROVED: {ticker} | Pushing to execution.")
            await self.queue_for_execution({
                **opportunity,
                "confidence": confidence,
                "variance": variance,
                "ev": sim_result.get('ev', 0),
                "debate_reasoning": debate_result.get('reasoning', '')
            })
        else:
            reason = "Low confidence" if confidence < self.CONFIDENCE_THRESHOLD else "High variance"
            await self.log(f"❌ VETOED: {ticker} | Reason: {reason}")

    async def run_debate(self, opportunity: Dict) -> Dict:
        """Multi-persona AI debate using Gemini"""
        if not self.model:
            await self.log("Gemini unavailable. Using heuristic confidence.")
            return {"confidence": opportunity.get('value_gap', 0) * 10, "reasoning": "Heuristic only"}
        
        ticker = opportunity.get('ticker', 'UNKNOWN')
        value_gap = opportunity.get('value_gap', 0)
        kalshi_price = opportunity.get('kalshi_price', 0.5)
        vegas_prob = opportunity.get('vegas_prob', 0.5)
        
        prompt = f"""You are a trading committee with two personas debating a market opportunity.

MARKET: {ticker}
Kalshi Price: {kalshi_price*100:.1f}%
Vegas/Pinnacle Probability: {vegas_prob*100:.1f}%
Value Gap: {value_gap*100:.1f}%

{f"Today's Trading Instructions: {self.trading_instructions[:500]}" if self.trading_instructions else ""}

OPTIMIST: Argue why this is a great opportunity. Be specific about the edge.
CRITIC: Argue against this trade. Point out risks and potential traps.
JUDGE: Based on both arguments, give a confidence score from 0-100.

Respond in JSON format:
{{"optimist": "...", "critic": "...", "judge_verdict": "...", "confidence": 85}}"""

        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.model.generate_content(prompt)
            )
            
            # Parse response
            text = response.text
            import json
            import re
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return {
                    "confidence": result.get('confidence', 50) / 100,
                    "reasoning": result.get('judge_verdict', '')
                }
        except Exception as e:
            await self.log(f"Debate error: {str(e)[:50]}", level="ERROR")
        
        return {"confidence": 0.5, "reasoning": "Debate failed"}

    def run_simulation(self, opportunity: Dict) -> Dict:
        """Monte Carlo simulation for variance and EV calculation"""
        vegas_prob = opportunity.get('vegas_prob', 0.5)
        kalshi_price = opportunity.get('kalshi_price', 0.5)
        
        # Simulate outcomes
        np.random.seed(42)  # Reproducibility
        outcomes = np.random.binomial(1, vegas_prob, self.SIMULATION_ITERATIONS)
        
        # Calculate returns per simulation
        # Win: (1 - kalshi_price) profit | Lose: kalshi_price loss
        returns = np.where(outcomes == 1, (1 - kalshi_price), -kalshi_price)
        
        win_rate = outcomes.mean()
        ev = returns.mean()
        variance = returns.var()
        
        return {
            "win_rate": win_rate,
            "ev": ev,
            "variance": variance
        }

    async def queue_for_execution(self, exec_queue: asyncio.Queue, target: Dict):
        """Push approved target to execution queue and Supabase"""
        execution_package = {
            "signal_id": str(uuid.uuid4()),
            "ticker": target.get('ticker', ''),
            "confidence": target.get('confidence', 0),
            "monte_carlo_ev": target.get('ev', 0),
            "reasoning": target.get('reasoning', ''),
            "suggested_size": target.get('suggested_size', 0),
            "status": "READY_TO_STRIKE"
        }
        await exec_queue.put(execution_package)
        await log_to_db("execution_queue", execution_package)
        await self.bus.publish("EXECUTION_READY", {
            "signal_id": execution_package["signal_id"],
            "confidence": execution_package["confidence"],
            "ev": execution_package["monte_carlo_ev"]
        }, self.name)

    def pop_execution_target(self) -> Optional[Dict]:
        """Get next target for Hand to execute"""
        return self.execution_queue.pop(0) if self.execution_queue else None

    async def run_intelligence(self, opp_queue: asyncio.Queue, exec_queue: asyncio.Queue):
        """Process opportunities into execution decisions."""
        while True:
            try:
                # Get next opportunity
                opportunity = await opp_queue.get()
                await self.log(f"Processing opportunity: {opportunity['market_id']}")

                # Run debate
                debate_result = await self.run_committee_debate(opportunity)
                confidence = debate_result.get('confidence', 0)

                # Run simulation
                sim_result = await self.run_monte_carlo_simulation(opportunity, debate_result)

                target = {
                    "ticker": opportunity['market_id'],
                    "confidence": confidence,
                    "ev": sim_result.get('ev', 0),
                    "reasoning": debate_result.get('reasoning', ''),
                    "suggested_size": self.calculate_kelly_stake(confidence, sim_result.get('ev', 0))
                }

                if confidence > 85:
                    await self.queue_for_execution(exec_queue, target)
                    await self.log(f"Approved for execution: {target['ticker']} | Conf: {confidence}%")
                else:
                    await self.log(f"Rejected: {target['ticker']} | Conf: {confidence}% too low")

            except Exception as e:
                await self.log(f"Intelligence error: {str(e)[:100]}", level="ERROR")
                await asyncio.sleep(1)

            await asyncio.sleep(1)  # Process frequently

    async def on_tick(self, payload: Dict[str, Any]):
        pass  # Brain is event-driven
