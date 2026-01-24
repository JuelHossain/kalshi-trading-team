"""
MEGA-AGENT 2: THE SENSES
Role: 24/7 Passive Observer

Workflow:
1. Passive Scout: Pure Python (Asyncio) loop scans all Kalshi markets (Zero token cost)
2. Shadow Odds Sync: Hits RapidAPI to fetch global Vegas/Pinnacle odds
3. The Filter: (Vegas_Prob - Kalshi_Price) > 5% triggers
4. Queue Management: Push high-value targets to Opportunity Queue
"""

import asyncio
import aiohttp
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from agents.base import BaseAgent
from core.bus import EventBus
from core.db import log_to_db

# RapidAPI Configuration
RAPIDAPI_KEY = os.environ.get("RAPID_API_KEY", "")
RAPIDAPI_HOST = "odds.p.rapidapi.com"


class SensesAgent(BaseAgent):
    """The 24/7 Observer - Surveillance & Signal Detection"""
    
    VALUE_GAP_THRESHOLD = 0.05  # 5% minimum edge required
    MIN_LIQUIDITY = 2000  # $2,000 minimum liquidity
    
    def __init__(self, agent_id: int, bus: EventBus, kalshi_client=None):
        super().__init__("SENSES", agent_id, bus)
        self.kalshi_client = kalshi_client
        self.opportunity_queue: List[Dict] = []
        self.vegas_odds_cache: Dict[str, float] = {}
        self.is_scanning = False

    async def setup(self):
        await self.log("Senses online. 24/7 passive surveillance activated.")
        await self.bus.subscribe("PREFLIGHT_COMPLETE", self.start_scan)
        await self.bus.subscribe("CYCLE_END", self.stop_scan)

    async def start_scan(self, message):
        """Begin passive market surveillance"""
        self.is_scanning = True
        await self.log("Initiating passive market scan (zero token cost)...")
        
        # Run surveillance loop
        await self.surveillance_loop()

    async def stop_scan(self, message):
        """Stop scanning at cycle end"""
        self.is_scanning = False
        await self.log("Surveillance paused. Cycle complete.")

    async def surveillance_loop(self):
        """Main scanning loop - pure Python, no AI tokens"""
        try:
            # 1. Fetch Kalshi markets
            markets = await self.fetch_kalshi_markets()
            await self.log(f"Scanned {len(markets)} Kalshi markets.")
            
            # 2. Fetch shadow odds from RapidAPI
            await self.sync_vegas_odds()
            
            # 3. Filter for value gaps
            opportunities = await self.filter_value_gaps(markets)
            
            if opportunities:
                await self.log(f"Found {len(opportunities)} value gap opportunities!")
                for opp in opportunities:
                    await self.queue_opportunity(opp)
            else:
                await self.log("No significant value gaps detected.")
                
            # 4. Signal Brain if opportunities exist
            if self.opportunity_queue:
                await self.bus.publish("OPPORTUNITIES_READY", {
                    "count": len(self.opportunity_queue),
                    "top": self.opportunity_queue[0] if self.opportunity_queue else None
                }, self.name)
                
        except Exception as e:
            await self.log(f"Surveillance error: {str(e)[:100]}", level="ERROR")

    async def fetch_kalshi_markets(self) -> List[Dict]:
        """Fetch active markets from Kalshi (zero token cost)"""
        if not self.kalshi_client:
            await self.log("Kalshi client unavailable. Using mock data.")
            return self._mock_markets()
        
        try:
            # Use shared Kalshi client
            markets = await self.kalshi_client.get_active_markets()
            return [m for m in markets if m.get('volume', 0) >= self.MIN_LIQUIDITY]
        except Exception as e:
            await self.log(f"Kalshi fetch error: {str(e)[:50]}", level="ERROR")
            return []

    async def sync_vegas_odds(self):
        """Fetch shadow/Vegas odds from RapidAPI"""
        if not RAPIDAPI_KEY:
            await self.log("RapidAPI key not configured. Skipping odds sync.")
            return
            
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "X-RapidAPI-Key": RAPIDAPI_KEY,
                    "X-RapidAPI-Host": RAPIDAPI_HOST
                }
                async with session.get(
                    f"https://{RAPIDAPI_HOST}/v4/sports/upcoming/odds",
                    headers=headers,
                    params={"regions": "us", "markets": "h2h"}
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        self._parse_vegas_odds(data)
                        await self.log(f"Shadow odds synced: {len(self.vegas_odds_cache)} markets.")
        except Exception as e:
            await self.log(f"RapidAPI sync failed: {str(e)[:50]}", level="ERROR")

    def _parse_vegas_odds(self, data: List[Dict]):
        """Parse RapidAPI response into odds cache"""
        for event in data:
            event_id = event.get('id', '')
            for bookmaker in event.get('bookmakers', []):
                if bookmaker.get('key') in ['pinnacle', 'draftkings', 'fanduel']:
                    for market in bookmaker.get('markets', []):
                        for outcome in market.get('outcomes', []):
                            key = f"{event_id}_{outcome.get('name', '')}"
                            # Convert American odds to probability
                            price = outcome.get('price', 0)
                            if price > 0:
                                prob = 100 / (price + 100)
                            else:
                                prob = abs(price) / (abs(price) + 100)
                            self.vegas_odds_cache[key] = prob

    async def filter_value_gaps(self, markets: List[Dict]) -> List[Dict]:
        """Find markets with Vegas probability > Kalshi price by threshold"""
        opportunities = []
        
        for market in markets:
            ticker = market.get('ticker', '')
            kalshi_price = market.get('yes_price', 50) / 100  # Convert cents to probability
            
            # Try to find matching Vegas odds
            vegas_prob = self.vegas_odds_cache.get(ticker, kalshi_price)
            
            value_gap = vegas_prob - kalshi_price
            
            if value_gap >= self.VALUE_GAP_THRESHOLD:
                opportunities.append({
                    "ticker": ticker,
                    "kalshi_price": kalshi_price,
                    "vegas_prob": vegas_prob,
                    "value_gap": value_gap,
                    "volume": market.get('volume', 0),
                    "market_data": market
                })
                
        # Sort by value gap (highest first)
        opportunities.sort(key=lambda x: x['value_gap'], reverse=True)
        return opportunities[:5]  # Top 5 only

    async def queue_opportunity(self, opp_queue: asyncio.Queue, opportunity: Dict):
        """Add opportunity to queue and Supabase"""
        signal_package = {
            "market_id": opportunity['ticker'],
            "source": opportunity.get('source', 'Kalshi'),
            "gap_delta": opportunity['value_gap'] * 100,  # As percentage
            "pinnacle_odds": opportunity['vegas_prob'],
            "kalshi_price": opportunity['kalshi_price'],
            "status": "QUEUED"
        }
        await opp_queue.put(signal_package)
        await log_to_db("opportunity_queue", signal_package)
        await self.log(f"Queued: {signal_package['market_id']} | Gap: {signal_package['gap_delta']:.1f}%")

    def pop_opportunity(self) -> Optional[Dict]:
        """Get next opportunity for Brain"""
        return self.opportunity_queue.pop(0) if self.opportunity_queue else None

    def _mock_markets(self) -> List[Dict]:
        """Mock market data for testing"""
        return [
            {"ticker": "NBA-LAKERS-WIN", "yes_price": 45, "volume": 5000},
            {"ticker": "NFL-CHIEFS-WIN", "yes_price": 52, "volume": 8000},
            {"ticker": "WEATHER-RAIN-NYC", "yes_price": 30, "volume": 3000},
        ]

    async def run_scout(self, opp_queue: asyncio.Queue):
        """Continuous scanning and queueing opportunities."""
        while True:
            try:
                await self.log("Initiating passive market scan (zero token cost)...")

                # Fetch Kalshi markets
                markets = await self.fetch_kalshi_markets()
                await self.log(f"Scanned {len(markets)} Kalshi markets.")

                # Sync Vegas odds
                await self.sync_vegas_odds()

                # Filter for value gaps
                opportunities = await self.filter_value_gaps(markets)
                await self.log(f"Found {len(opportunities)} value gaps.")

                # Queue opportunities
                for opp in opportunities:
                    await self.queue_opportunity(opp_queue, opp)

                if not opportunities:
                    await self.log("No significant value gaps detected.")

            except Exception as e:
                await self.log(f"Surveillance error: {str(e)[:100]}", level="ERROR")

            await asyncio.sleep(10)  # Scan every 10 seconds

    async def on_tick(self, payload: Dict[str, Any]):
        pass  # Surveillance is event-driven, not tick-based
