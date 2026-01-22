import os
import json
import asyncio
from typing import Dict, Any
from agents.base import BaseAgent
from core.bus import EventBus
from colorama import Fore, Style

try:
    from groq import AsyncGroq
except ImportError:
    pass

class AuditorAgent(BaseAgent):
    """
    Agent 6: The Auditor (Pessimist / Devil's Advocate)
    Role: Committee Veto & Risk Filtering.
    Uses Llama 3.1 70B via Groq for high-speed cynical analysis.
    """
    
    CONSENSUS_THRESHOLD = 85  # 85% average confidence required

    async def setup(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            await self.log("GROQ_API_KEY missing. Auditor Offline.", level="ERROR")
            return

        self.client = AsyncGroq(api_key=self.api_key)
        await self.log("Llama 3.1 70B Online. Role: Pessimist Auditor.")
        
        # Subscribe to Simulation Results to finalize the vetting
        await self.bus.subscribe("SIM_RESULT", self.handle_audit_request)

    async def handle_audit_request(self, message):
        data = message.payload
        ticker = data.get('ticker')
        
        # We need the Analyst's original arg/confidence too. 
        # In a more complex bus, we'd query state or join messages.
        # For now, we assume sim data carries it or we fetch from shared memory.
        await self.log(f"Auditing trade proposal for {ticker}...")
        
        # Cynical Analysis via Groq
        audit_result = await self.run_cynical_audit(ticker, data)
        
        # Calculate Consensus
        # (Mocking original analyst confidence if missing from payload)
        analyst_conf = 75 # placeholder
        avg_confidence = (analyst_conf + audit_result.get('auditorConfidence', 0)) / 2
        
        if avg_confidence >= self.CONSENSUS_THRESHOLD:
             await self.log(f"{Fore.GREEN}AUDIT PASSED: Consensus {avg_confidence:.1f}% >= 85%. Proceeding.{Style.RESET_ALL}")
             audit_result['approved'] = True
        else:
             await self.log(f"{Fore.RED}AUDIT VETO: Consensus {avg_confidence:.1f}% < 85%. Trade rejected.{Style.RESET_ALL}")
             audit_result['approved'] = False

        payload = {
            "ticker": ticker,
            "avg_confidence": avg_confidence,
            **audit_result
        }
        await self.bus.publish("AUDIT_DECISION", payload, self.name)

    async def run_cynical_audit(self, ticker: str, sim_data: Dict) -> Dict[str, Any]:
        if not self.client:
            return {"approved": False, "auditorConfidence": 0, "reason": "Groq Offline"}

        prompt = f"""
        Review this trade proposal for prediction market: "{ticker}".
        Simulation Win Rate: {sim_data.get('win_rate', 0)*100:.1f}%
        EV Score: {sim_data.get('ev_score', 0):.2f}
        
        You are the Pessimist Auditor. Your job is to find reasons why this trade will FAIL. 
        Be cynical, paranoid, and highlight counter-arguments.
        
        Output Strictly JSON:
        {{
            "reason": "string (cynical observation)",
            "auditorConfidence": int (0-100 score of YOUR confidence in success),
            "risk_factors": ["list", "of", "risks"]
        }}
        """
        
        try:
            response = await self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a pessimistic financial auditor."},
                    {"role": "user", "content": prompt}
                ],
                model="llama-3.1-70b-versatile",
                response_format={"type": "json_object"}
            )
            
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            await self.log(f"Audit failed: {e}")
            return {"approved": False, "auditorConfidence": 0, "reason": "API Failure"}
