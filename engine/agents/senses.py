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
import os
from datetime import datetime
from typing import Any

from agents.base import BaseAgent
from core.bus import EventBus
from core.db import log_to_db

# RapidAPI Configuration
RAPIDAPI_KEY = os.environ.get("RAPID_API_KEY", "")
RAPIDAPI_HOST = "odds.p.rapidapi.com"


from core.synapse import MarketData, Opportunity, Synapse

try:
    from ddgs import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False
    print("[SENSES] Warning: ddgs package not available. Install with: pip install ddgs")

class SensesAgent(BaseAgent):
    """The 24/7 Observer - Surveillance & Signal Detection"""

    MIN_LIQUIDITY = 0  # $0 minimum liquidity for Demo/Testing

    def __init__(self, agent_id: int, bus: EventBus, kalshi_client=None, synapse: Synapse = None):
        super().__init__("SENSES", agent_id, bus, synapse)
        self.kalshi_client = kalshi_client
        self.opportunity_queue: list[dict] = []
        self.is_scanning = False

    async def fetch_market_context(self, ticker: str, title: str) -> list[str]:
        """Fetch external context (news) for a market"""
        if not DDGS_AVAILABLE:
            return ["Search unavailable"]

        try:
            # Run simple search with timeout
            query = f"{title} news"
            loop = asyncio.get_event_loop()

            # Use wait_for to add timeout to the executor call
            results = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: list(DDGS(proxy=None).text(query, max_results=3))
                ),
                timeout=10.0  # 10 second timeout for search
            )
            return [r.get("body", "") for r in results]
        except asyncio.TimeoutError:
            await self.log(f"Search timeout for {ticker}", level="WARN")
            return []
        except Exception as e:
            await self.log(f"Search error for {ticker}: {str(e)[:50]}", level="WARN")
            return []

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

            await self.log(f"Scanning {len(markets)} Kalshi markets...")

            # 2. Select Top 10 by Volume (Liquidity Priority)
            opportunities = await self.select_top_opportunities(markets)

            if opportunities:
                await self.log(f"Selected {len(opportunities)} high-volume opportunities for queuing...")
                queued_count = 0
                for opp in opportunities:
                    await self.queue_opportunity(opp)
                    queued_count += 1

                await self.log(f"Queue Summary: {queued_count} opportunities queued successfully")

                # Verify queue size
                if self.synapse:
                    queue_size = await self.synapse.opportunities.size()
                    await self.log(f"Synapse Queue Size: {queue_size}", level="INFO")

                # 3. Signal Brain if opportunities exist
                await self.bus.publish(
                    "OPPORTUNITIES_READY",
                    {
                        "count": queued_count,
                        "source": "SENSES",
                    },
                    self.name,
                )
                await self.log("Signaled Brain: OPPORTUNITIES_READY event published")
            else:
                await self.log("WARNING: No significant opportunities detected", level="WARN")

        except Exception as e:
            await self.log(f"Surveillance error: {str(e)[:100]}", level="ERROR")

    async def fetch_kalshi_markets(self) -> list[dict]:
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

            if not isinstance(markets, list):
                await self.log(
                    f"ERROR: Expected list of markets, got {type(markets).__name__}",
                    level="ERROR",
                )
                return []

            await self.log(f"Fetched {len(markets)} markets from Kalshi API", level="INFO")

            # Log sample market for debugging
            if len(markets) > 0:
                sample = markets[0]
                ticker = sample.get("ticker", "NO_TICKER")
                volume = sample.get("volume", 0)
                await self.log(f"Sample market: {ticker} | Volume: {volume}", level="DEBUG")
            else:
                await self.log("WARNING: No markets returned from Kalshi API", level="WARN")

            return markets

        except Exception as e:
            await self.log(f"Kalshi fetch error: {str(e)[:100]}", level="ERROR")
            return []

    async def select_top_opportunities(self, markets: list[dict]) -> list[dict]:
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

            title = market.get("title", ticker)
            
            # Fetch context
            context_snippets = await self.fetch_market_context(ticker, title)
            context_str = "\\n".join(context_snippets)

            # Define opportunity without external odds
            # Note: value_gap removed - Brain uses AI estimation, not external odds comparison
            opportunities.append(
                {
                    "ticker": ticker,
                    "kalshi_price": kalshi_price,
                    "vegas_prob": None,  # Signal to Brain to use AI estimation
                    "volume": volume,
                    "market_data": market,
                    "source": "Volume-Algo",
                    "external_context": context_str
                }
            )

        # Log filtering results with market details
        await self.log(f"Selected {len(opportunities)} top markets by volume", level="INFO")
        for i, opp in enumerate(opportunities, 1):
            ticker = opp.get("ticker", "UNKNOWN")
            volume = opp.get("volume", 0)
            price = opp.get("kalshi_price", 0)
            await self.log(f"  {i}. {ticker} | Vol: ${volume} | Price: {price*100:.1f}c", level="DEBUG")

        max_vol = opportunities[0]['volume'] if opportunities else 0
        await self.log(f"Max Volume: ${max_vol}", level="INFO")
        return opportunities

    async def queue_opportunity(self, opportunity: dict):
        """Add opportunity to Synapse queue (primary) and legacy queue (fallback)"""
        ticker = opportunity.get("ticker", "UNKNOWN")
        volume = opportunity.get("volume", 0)

        # Synapse Integration (Primary Queue)
        synapse_success = False
        if self.synapse:
            try:
                # Basic Mapping
                m_data = opportunity.get("market_data", {})
                def g(k, d=None): return m_data.get(k, d)

                market_payload = MarketData(
                    ticker=ticker,
                    title=g("title", "Unknown"),
                    subtitle=g("subtitle", ""),
                    yes_price=int(opportunity.get("kalshi_price", 0) * 100),
                    no_price=g("no_price", 0),
                    volume=int(g("volume", 0)),
                    expiration=g("expiration_time", str(datetime.now())),
                    raw_response=m_data
                )

                opp_model = Opportunity(
                    ticker=ticker,
                    market_data=market_payload,
                    source="SENSES",
                )

                await self.synapse.opportunities.push(opp_model)

                # Verify the push succeeded by checking queue size
                queue_size = await self.synapse.opportunities.size()
                await self.log(f"[OK] Queued to Synapse: {ticker} (Queue Size: {queue_size}) | Volume: {volume}")
                synapse_success = True

            except Exception as e:
                await self.log(f"[FAIL] Synapse Push Failed for {ticker}: {e}", level="ERROR")
                synapse_success = False

        # Legacy Flow (Fallback - only if Synapse failed or not available)
        if not synapse_success or not self.synapse:
            signal_package = {
                "market_id": ticker,
                "source": opportunity.get("source", "Kalshi"),
                "gap_delta": 0,
                "pinnacle_odds": 0,
                "kalshi_price": opportunity.get("kalshi_price", 0),
                "status": "QUEUED",
                "market_data": opportunity.get("market_data", {})
            }
            self.opportunity_queue.append(opportunity)
            await log_to_db("opportunity_queue", signal_package)
            await self.log(f"[WARN] Fallback to Legacy Queue: {ticker} | Volume: {volume}", level="WARN")

    def pop_opportunity(self) -> dict | None:
        """Get next opportunity for Brain"""
        return self.opportunity_queue.pop(0) if self.opportunity_queue else None

    async def run_scout(self, opp_queue: asyncio.Queue):
        """DEPRECATED: Continuous scanning disabled - now scans only on cycle start."""
        # This method is deprecated and no longer called
        await self.log("WARNING: run_scout called but is deprecated. Scans now happen on cycle start only.", level="WARN")
        pass

    async def on_tick(self, payload: dict[str, Any]):
        pass
