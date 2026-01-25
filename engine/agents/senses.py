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

    MIN_LIQUIDITY = 0  # $0 minimum liquidity for Demo/Testing

    def __init__(self, agent_id: int, bus: EventBus, kalshi_client=None):
        super().__init__("SENSES", agent_id, bus)
        self.kalshi_client = kalshi_client
        self.opportunity_queue: List[Dict] = []
        self.is_scanning = False

    async def setup(self):
        await self.log("Senses online. 24/7 passive surveillance activated.")
        await self.bus.subscribe("PREFLIGHT_COMPLETE", self.start_scan)
        await self.bus.subscribe("CYCLE_END", self.stop_scan)

    async def start_scan(self, message):
        """Begin passive market surveillance"""
        self.is_scanning = True
        await self.log("Initiating passive market scan (zero token cost)...")

        # Run surveillance loop once
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
            
            if not markets:
                await self.log("No markets found to scan.", level="WARN")
                return

            await self.log(f"Scanned {len(markets)} Kalshi markets.")

            # 2. Select Top 10 by Volume (Liquidity Priority)
            opportunities = await self.select_top_opportunities(markets)

            if opportunities:
                await self.log(f"Selected {len(opportunities)} high-volume opportunities for analysis.")
                for opp in opportunities:
                    await self.queue_opportunity(opp)
            else:
                await self.log("WARNING: No significant opportunities detected", level="WARN")

            # 3. Signal Brain if opportunities exist
            if self.opportunity_queue:
                await self.bus.publish(
                    "OPPORTUNITIES_READY",
                    {
                        "count": len(self.opportunity_queue),
                        "top": self.opportunity_queue[0] if self.opportunity_queue else None,
                    },
                    self.name,
                )

        except Exception as e:
            await self.log(f"Surveillance error: {str(e)[:100]}", level="ERROR")

    async def fetch_kalshi_markets(self) -> List[Dict]:
        """Fetch active markets from Kalshi"""
        if not self.kalshi_client:
            await self.log("ERROR: Kalshi client not initialized.", level="ERROR")
            return []

        try:
            # Use shared Kalshi client
            markets = await self.kalshi_client.get_active_markets()
            
            if markets is None:
                await self.log(
                    "ERROR: Kalshi API request failed - check network and credentials",
                    level="ERROR",
                )
                return []
                
            await self.log(f"DEBUG: Active markets fetched: {len(markets)}", level="INFO")
            
            # Simple filter for demo: Active status is handled by API
            return markets
            
        except Exception as e:
            await self.log(f"Kalshi fetch error: {str(e)[:100]}", level="ERROR")
            return []

    async def select_top_opportunities(self, markets: List[Dict]) -> List[Dict]:
        """Select Top 10 Markets by Volume"""
        opportunities = []

        # 1. Sort by Volume (Descending)
        sorted_markets = sorted(markets, key=lambda x: x.get("volume", 0), reverse=True)
        
        # 2. Pick Top 10
        top_markets = sorted_markets[:10]

        for market in top_markets:
            ticker = market.get("ticker", "")
            kalshi_price = market.get("yes_price", 50) / 100  # Convert cents to probability
            volume = market.get("volume", 0)

            # Define opportunity without external odds
            opportunities.append(
                {
                    "ticker": ticker,
                    "kalshi_price": kalshi_price,
                    "vegas_prob": None, # Signal to Brain to use AI estimation
                    "value_gap": 0, # Placeholder
                    "volume": volume,
                    "market_data": market,
                    "source": "Volume-Algo"
                }
            )

        # Log filtering results
        await self.log(f"Selection Report: Picked top {len(opportunities)} markets by volume. Max Vol: {opportunities[0]['volume'] if opportunities else 0}", level="INFO")
        return opportunities

    async def queue_opportunity(self, opportunity: Dict):
        """Add opportunity to queue and Supabase"""
        signal_package = {
            "market_id": opportunity["ticker"],
            "source": opportunity.get("source", "Kalshi"),
            "gap_delta": 0,  
            "pinnacle_odds": 0,
            "kalshi_price": opportunity["kalshi_price"],
            "status": "QUEUED",
            "market_data": opportunity.get("market_data", {})
        }
        self.opportunity_queue.append(opportunity) # Local queue for Brain to pop via pop_opportunity()
        await log_to_db("opportunity_queue", signal_package)
        await self.log(
            f"Queued: {signal_package['market_id']} | Vol: {opportunity['volume']}"
        )

    def pop_opportunity(self) -> Optional[Dict]:
        """Get next opportunity for Brain"""
        return self.opportunity_queue.pop(0) if self.opportunity_queue else None

    async def run_scout(self, opp_queue: asyncio.Queue):
        """Continuous scanning and queueing opportunities (called by Engine)."""
        while True:
            try:
                if self.is_scanning:
                     # Reuse surveillance loop logic
                    markets = await self.fetch_kalshi_markets()
                    if markets:
                        opportunities = await self.select_top_opportunities(markets)
                        for opp in opportunities:
                            # We push to internal queue for Brain (who calls pop_opportunity)
                             await self.queue_opportunity(opp)
                             
                             # We also put to the Engine's async queue if it's used elsewhere?
                             # Engine passes opp_queue but Brain doesn't use it in `run_brain`.
                             # Brain calls `self.senses.pop_opportunity()`.
                             # So opp_queue is largely redundant in this architecture, but I'll write to it just in case.
                             await opp_queue.put(opp)
                    
                    if not markets:
                         await self.log("No markets found.", level="WARN")

            except Exception as e:
                await self.log(f"Surveillance error: {str(e)[:100]}", level="ERROR")

            await asyncio.sleep(10)  # Scan every 10 seconds

    async def on_tick(self, payload: Dict[str, Any]):
        pass
