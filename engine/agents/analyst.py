import os
import json
import asyncio
from typing import Dict, Any
from agents.base import BaseAgent
from core.bus import EventBus

try:
    import google.generativeai as genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
except ImportError:
    pass

class AnalystAgent(BaseAgent):
    """
    Agent 4: The Analyst (Gemini 1.5 Pro)
    Role: The Optimist.
    Finds alpha and structural reasons to enter a trade.
    """
    
    def __init__(self, agent_id: int, bus: EventBus):
        super().__init__("ANALYST", agent_id, bus)
    
    async def setup(self):
        self.api_key = os.getenv("GEMINI_API_KEY") or os.getenv("API_KEY")
        if not self.api_key:
            await self.log("GEMINI_API_KEY missing. Analyst Offline.", level="ERROR")
            return

        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        await self.log("Gemini 2.0 Flash Online. Playing role: Optimist.")
        
        await self.bus.subscribe("INTERCEPT_DATA", self.handle_analysis_request)

    async def handle_analysis_request(self, message):
        data = message.payload
        ticker = data.get('ticker')
        if not ticker: return
        
        await self.log(f"Analyzing {ticker} for Alpha...")
        analysis_result = await self.run_debate(ticker)
        await self.bus.publish("ANALYST_VERDICT", analysis_result, self.name)

    async def run_debate(self, market_title: str) -> Dict[str, Any]:
        if not self.model:
            return {"judgeVerdict": "Neutral", "confidenceScore": 0}

        prompt = f"""
        Conduct a 'Committee Debate' for the Kalshi prediction market: "{market_title}".
        You are the Analyst (Optimist): Focus on positive alpha.
        Output JSON with: optimistArg, judgeVerdict, confidenceScore (0-100).
        """
        
        try:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(None, lambda: self.model.generate_content(prompt))
            text = response.text.replace('```json', '').replace('```', '').strip()
            return json.loads(text)
        except Exception as e:
            await self.log(f"Analysis Failed: {e}", level="ERROR")
            return {"judgeVerdict": "Error", "confidenceScore": 0}
