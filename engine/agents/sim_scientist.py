import asyncio
import numpy as np
from typing import Dict, Any
from agents.base import BaseAgent
from core.bus import EventBus
from colorama import Fore, Style

class SimScientistAgent(BaseAgent):
    """
    Agent 5: The Sim Scientist (Monte Carlo Engine)
    Role: High-performance statistical validation.
    Calculates EV and Win Probability across 10,000 simulations.
    """
    
    SIMULATION_COUNT = 10000
    VETO_THRESHOLD = 0.58  # 58% Win Rate


    async def setup(self):
        await self.log("Monte Carlo Engine Online. Preparing 10,000 iterations.")
        # Listen for Analyst verdicts to validate
        await self.bus.subscribe("ANALYST_VERDICT", self.handle_verdict_validation)

    async def handle_verdict_validation(self, message):
        data = message.payload
        ticker = data.get('ticker')
        analyst_confidence = data.get('confidenceScore', 50) / 100.0
        
        await self.log(f"Simulating outcomes for {ticker} (Confidence: {analyst_confidence*100:.1f}%)...")
        
        # Run Monte Carlo in executor (though NumPy is fast, keep loop free)
        loop = asyncio.get_running_loop()
        sim_result = await loop.run_in_executor(None, self.run_simulation, analyst_confidence)
        
        # Check Veto
        win_rate = sim_result['win_rate']
        if win_rate < self.VETO_THRESHOLD:
            await self.log(f"{Fore.YELLOW}SIM VETO: Win-rate {win_rate*100:.1f}% < 58%. Warning. {Style.RESET_ALL}")
            sim_result['veto'] = True
        else:
            sim_result['veto'] = False

        # Publish Simulation Result
        payload = {
            "ticker": ticker,
            **sim_result
        }
        await self.bus.publish("SIM_RESULT", payload, self.name)

    def run_simulation(self, confidence: float) -> Dict[str, Any]:
        """
        Core NumPy Monte Carlo Engine.
        Simulates binary outcomes adjusted for target confidence.
        """
        # Historical standard deviation (mocked for now, in prod retrieved from Historian)
        std_dev = 0.15 
        
        # Generate varied probabilities around the mean (Analyst Confidence)
        outcomes = np.random.normal(confidence, std_dev, self.SIMULATION_COUNT)
        
        # Calculate win rate (Outcomes > 0.5 considered success)
        wins = outcomes[outcomes > 0.5]
        win_rate = len(wins) / self.SIMULATION_COUNT
        
        # Calculate EV Score (Simplified: (WinRate * ProfitFactor) - LossRate)
        # Assuming 1:1 reward ratio for basic EV calculation
        ev_score = (win_rate * 1.0) - (1.0 - win_rate)
        
        variance = np.var(outcomes)
        
        return {
            "win_rate": win_rate,
            "ev_score": float(ev_score),
            "variance": float(variance),
            "iterations": self.SIMULATION_COUNT,
            "report": f"MC completed {self.SIMULATION_COUNT} cycles. EV: {ev_score:.2f} | Var: {variance:.4f}"
        }
