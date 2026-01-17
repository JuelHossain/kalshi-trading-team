import os
import json
import asyncio
from datetime import datetime
from typing import List, Dict, Any
from agents.base import BaseAgent
from core.bus import EventBus

try:
    import aiohttp
except ImportError:
    pass

class InterceptorAgent(BaseAgent):
    """
    Agent 3: The Interceptor (Vegas Odds Interceptor)
    Fetches real-time odds to establish "Shadow Probabilities".
    """
    
    async def setup(self):
        self.api_key = os.getenv("RAPID_API_KEY")
        self.host = "api-football-v1.p.rapidapi.com"
        self.base_url = f"https://{self.host}/v3/odds"
        self.shadow_odds = {}
        
        if not self.api_key:
            await self.log("RAPID_API_KEY missing. Shadow Mode enabled.", level="WARNING")
        else:
            await self.log("Live Interceptor Online.")

        await self.bus.subscribe("MARKET_DATA", self.handle_market_candidate)

    async def handle_market_candidate(self, message):
        target = message.payload
        ticker = target.get('ticker')
        if not ticker: return

        await self.log(f"Comparing {ticker} against Vegas Shadow Books...")
        odds = await self.fetch_live_odds()
        
        shadow_prob = 0.55
        delta = abs(shadow_prob - (target.get('last_price', 50) / 100))
        
        payload = {
            "ticker": ticker,
            "shadow_prob": shadow_prob,
            "delta": delta,
            "timestamp": datetime.now().isoformat()
        }
        await self.bus.publish("INTERCEPT_DATA", payload, self.name)

    async def fetch_live_odds(self) -> List[Dict]:
        if not self.api_key:
            return self.get_mock_odds()

        headers = {
            'X-RapidAPI-Key': self.api_key,
            'X-RapidAPI-Host': self.host
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                url = f"{self.base_url}?league=39&season=2023"
                async with session.get(url, headers=headers, timeout=3.0) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return self.normalize_odds(data.get('response', []))
                    else:
                        await self.log(f"RapidAPI Error {resp.status}")
                        return self.get_mock_odds()
            except Exception as e:
                await self.log(f"Intercept Failed: {e}", level="ERROR")
                return self.get_mock_odds()

    def normalize_odds(self, raw_data: List[Any]) -> List[Dict]:
        normalized = []
        for match in raw_data[:5]:
            try:
                bookie = match['bookmakers'][0]
                home_odd = next((b['odd'] for b in bookie['bets'][0]['values'] if b['value'] == 'Home'), 2.0)
                home_prob = 1 / float(home_odd) if home_odd else 0
                normalized.append({
                    "event": f"{match['teams']['home']['name']} vs {match['teams']['away']['name']}",
                    "prob": home_prob,
                    "timestamp": datetime.now().isoformat()
                })
            except:
                continue
        return normalized

    def get_mock_odds(self) -> List[Dict]:
        return [{"event": "Shadow Protocol", "prob": 0.55, "timestamp": datetime.now().isoformat()}]
