import asyncio
from typing import Dict, Any, List
from pydantic import BaseModel
from agents.base import BaseAgent
from core.bus import EventBus
from core.network import kalshi_client
from colorama import Fore, Style

class MarketCandidate(BaseModel):
    ticker: str
    title: str
    volume: int
    last_price: int

class ScoutAgent(BaseAgent):
    """
    Agent 2: The Scout (Global Market Scanner)
    Optimized for Sentient Alpha v2.
    """
    
    async def setup(self):
        await self.log("Scout initialized and connected to Kalshi via shared client.")

    async def on_tick(self, payload: Dict[str, Any]):
        cycle = payload.get('cycle', 0)
        
        # Scan every 10 ticks
        if cycle % 10 == 0:
            await self.log("Scanning Markets...")
            markets = await kalshi_client.get_markets(limit=100)
            await self.analyze_markets(markets)

    async def analyze_markets(self, markets: List[Dict]):
        # Filter for liquidity
        candidates = []
        for m in markets:
             # Basic Liquidity Filter: Volume > 10
             if m.get('volume', 0) > 10:
                 try:
                     candidate = MarketCandidate(
                         ticker=m.get('ticker'),
                         title=m.get('title'),
                         volume=m.get('volume', 0),
                         last_price=m.get('last_price', 50)
                     )
                     candidates.append(candidate)
                 except Exception as e:
                     await self.log(f"Failed to parse market {m.get('ticker')}: {e}", level="ERROR")
        
        await self.log(f"Scanned {len(markets)} markets. Found {len(candidates)} active candidates.")
        
        # Publish candidates to bus
        if candidates:
            # Sort by volume desc
            candidates.sort(key=lambda x: x.volume, reverse=True)
            top_pick = candidates[0]
            
            await self.bus.publish("MARKET_DATA", top_pick.model_dump(), self.name)
