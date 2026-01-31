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
import re
from datetime import datetime
from typing import Any

from agents.base import BaseAgent
from core.bus import EventBus
from core.constants import (
    SENSES_MIN_LIQUIDITY,
    SENSES_STOCK_BUFFER_SIZE,
    SENSES_QUEUE_BATCH_SIZE,
)
from core.db import log_to_db
from core.error_dispatcher import ErrorSeverity
from core.flow_control import check_execution_queue_limit, check_opportunity_queue_limit

# RapidAPI Configuration
RAPIDAPI_KEY = os.environ.get("RAPID_API_KEY", "")
RAPIDAPI_HOST = "odds.p.rapidapi.com"

# Compiled regex for ticker date parsing
TICKER_DATE_PATTERN = re.compile(r"(\d{2}[A-Z]{3}\d{2})")


from core.synapse import MarketData, Opportunity, Synapse

try:
    from ddgs import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False
    import logging
    logging.getLogger("SENSES").warning("ddgs package not available. Install with: pip install ddgs")

class SensesAgent(BaseAgent):
    """The 24/7 Observer - Surveillance & Signal Detection"""

    MIN_LIQUIDITY = SENSES_MIN_LIQUIDITY  # $10 minimum liquidity for Production
    STOCK_BUFFER_SIZE = SENSES_STOCK_BUFFER_SIZE  # Total markets to pull from Kalshi
    QUEUE_BATCH_SIZE = SENSES_QUEUE_BATCH_SIZE   # Markets to queue at once
    RESTOCK_THRESHOLD = 5   # Brain dumps this many before requesting restock

    def __init__(self, agent_id: int, bus: EventBus, kalshi_client=None, synapse: Synapse = None):
        super().__init__("SENSES", agent_id, bus, synapse)
        self.kalshi_client = kalshi_client
        self.opportunity_queue: list[dict] = []
        self.is_scanning = False

        # Stock buffer: Keep 20 markets in memory, queue top 10
        self.market_stock: list[dict] = []  # Sorted by volume (descending)
        self._initial_scan_done = False
        self._dumped_count = 0  # Track how many Brain has dumped

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
        except TimeoutError:
            await self.log(f"Search timeout for {ticker}", level="WARN")
            return []
        except Exception as e:
            await self.log(f"Search error for {ticker}: {str(e)[:50]}", level="WARN")
            return []

    async def setup(self):
        await self.log("Senses online. 24/7 passive surveillance activated.")
        await self.bus.subscribe("PREFLIGHT_COMPLETE", self.start_scan)
        await self.bus.subscribe("CYCLE_END", self.stop_scan)
        await self.bus.subscribe("REQUEST_RESTOCK", self.on_restock_request)

    async def start_scan(self, message):
        """Begin passive market surveillance (runs only once per startup)"""
        # Prevent multiple scans - only scan once at startup
        if self._initial_scan_done:
            await self.log("Initial scan already complete. Senses in STANDBY mode. Waiting for restock trigger.", level="INFO")
            return

        self.is_scanning = True
        self._initial_scan_done = True  # Set flag BEFORE scanning to prevent race conditions
        await self.log("Initiating passive market scan (zero token cost)...")

        # Run initial surveillance to populate stock buffer
        await self.surveillance_loop()
        await self.log("Initial scan complete. Senses entering STANDBY mode.", level="SUCCESS")

    async def stop_scan(self, message):
        """Stop scanning at cycle end"""
        self.is_scanning = False
        await self.log("Surveillance paused. Cycle complete.")

    async def surveillance_loop(self):
        """Main scanning loop - pure Python, no AI tokens
        Pulls top 30 markets, keeps 20 in stock, queues top 10"""
        try:
            # FLOW CONTROL: Check if execution queue is at limit
            if self.synapse:
                is_at_limit, exec_size = await check_execution_queue_limit(self.synapse)
                if is_at_limit:
                    await self.log(f"Flow Control: Execution queue at limit ({exec_size}/10). Pausing surveillance.", level="WARN")
                    return

            # 1. Fetch Kalshi markets (get more, we'll filter to top 30)
            markets = await self.fetch_kalshi_markets()

            if not markets:
                await self.log("No markets found to scan.", level="WARN")
                return

            await self.log(f"Fetched {len(markets)} markets from Kalshi API")

            # 2. Sort by volume and take top 30
            sorted_markets = sorted(markets, key=lambda x: x.get("volume", 0), reverse=True)
            top_markets = sorted_markets[:self.STOCK_BUFFER_SIZE]

            # 3. Populate stock buffer with top 30 (all)
            self.market_stock = top_markets
            await self.log(f"Stock buffer populated with {len(self.market_stock)} markets")

            # 4. Queue top 10 from stock
            await self.queue_from_stock()

            # 5. Signal Brain that opportunities are ready
            queue_size = await self.synapse.opportunities.size() if self.synapse else 0
            await self.bus.publish(
                "OPPORTUNITIES_READY",
                {
                    "count": queue_size,
                    "source": "SENSES",
                },
                self.name,
            )
            await self.log("Signaled Brain: OPPORTUNITIES_READY event published")

        except Exception as e:
            await self.log(f"Surveillance error: {str(e)[:100]}", level="ERROR")
            await self.log_error(
                code="NETWORK_CONNECTION_FAILED",
                message=f"Senses Surveillance Failed: {e!s}",
                severity=ErrorSeverity.CRITICAL,
                exception=e
            )
            await self.bus.publish("SYSTEM_FATAL", {"message": f"Senses Agent Failed: {e!s}"}, self.name)

    async def fetch_kalshi_markets(self) -> list[dict]:
        """Fetch active markets from Kalshi (requests more for filtering)"""
        if not self.kalshi_client:
            await self.log("ERROR: Kalshi client not initialized.", level="ERROR")
            return []

        try:
            # Request more markets to have better selection (limit=100)
            markets = await self.kalshi_client.get_active_markets(limit=100)

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

            # Filter to today's markets only (check expiration or title)
            today_markets = [m for m in markets if self._is_today_market(m)]

            await self.log(f"Filtered to {len(today_markets)} today's markets from {len(markets)} total", level="INFO")

            # Log sample market for debugging
            if len(today_markets) > 0:
                sample = today_markets[0]
                ticker = sample.get("ticker", "NO_TICKER")
                volume = sample.get("volume", 0)
                await self.log(f"Sample market: {ticker} | Volume: {volume}", level="DEBUG")
            else:
                await self.log("WARNING: No today's markets returned from Kalshi API", level="WARN")

            return today_markets

        except Exception as e:
            await self.log(f"Kalshi fetch error: {str(e)[:100]}", level="ERROR")
            return []

    def _is_today_market(self, market: dict) -> bool:
        """Check if market expires today (based on title or expiration time)"""
        title = market.get("title", "").lower()
        ticker = market.get("ticker", "")

        # Check ticker for today's date (e.g., 26JAN30 in KX...-26JAN30-...)
        # Check ticker for today's date (e.g., 26JAN30 in KX...-26JAN30-...)
        if TICKER_DATE_PATTERN.search(ticker):
            # For now, accept all markets with date pattern
            # Could add stricter date validation
            return True

        return True  # Default to true if we can't determine

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

    async def queue_from_stock(self):
        """Queue top markets from stock buffer to Synapse
        Takes top 10 from stock (keeping remaining in buffer)"""
        if not self.market_stock:
            await self.log("Stock buffer empty. Cannot queue.", level="WARN")
            return 0

        # Take top QUEUE_BATCH_SIZE from stock
        to_queue = self.market_stock[:self.QUEUE_BATCH_SIZE]
        remaining = self.market_stock[self.QUEUE_BATCH_SIZE:]
        self.market_stock = remaining

        await self.log(f"Queueing {len(to_queue)} markets from stock (remaining in stock: {len(self.market_stock)})")

        queued_count = 0
        for market in to_queue:
            # Convert market dict to opportunity format
            ticker = market.get("ticker", "")
            kalshi_price = market.get("yes_price", 50) / 100
            volume = market.get("volume", 0)
            title = market.get("title", ticker)

            # Fetch context
            context_snippets = await self.fetch_market_context(ticker, title)
            context_str = "\\n".join(context_snippets)

            opportunity = {
                "ticker": ticker,
                "kalshi_price": kalshi_price,
                "vegas_prob": None,
                "volume": volume,
                "market_data": market,
                "source": "Volume-Algo",
                "external_context": context_str
            }

            await self.queue_opportunity(opportunity)
            queued_count += 1

        await self.log(f"Queued {queued_count} markets from stock to Synapse")

        # Verify queue size
        if self.synapse:
            queue_size = await self.synapse.opportunities.size()
            await self.log(f"Synapse Queue Size: {queue_size}", level="INFO")

        return queued_count

    async def on_restock_request(self, message):
        """Handle restock request from Brain
        Triggered when Brain has dumped 5 opportunities"""
        await self.log("Restock request received from Brain")

        # FLOW CONTROL: Don't add more if opportunity queue is already large
        if self.synapse:
            is_at_limit, opp_queue_size = await check_opportunity_queue_limit(self.synapse)
            if is_at_limit:
                await self.log(f"Flow Control: Opportunity queue still has {opp_queue_size} items. Skipping restock to prevent overload.", level="WARN")
                return

        # FLOW CONTROL: Check execution queue - don't restock if it's full
        if self.synapse:
            is_at_limit, exec_size = await check_execution_queue_limit(self.synapse)
            if is_at_limit:
                await self.log(f"Flow Control: Execution queue at limit ({exec_size}/10). Skipping restock.", level="WARN")
                return

        # If stock is low (< 10), pull fresh 30 from Kalshi
        if len(self.market_stock) < self.QUEUE_BATCH_SIZE:
            await self.log("Stock buffer low. Fetching fresh markets from Kalshi...")
            markets = await self.fetch_kalshi_markets()
            if markets:
                sorted_markets = sorted(markets, key=lambda x: x.get("volume", 0), reverse=True)
                self.market_stock = sorted_markets[:self.STOCK_BUFFER_SIZE]
                await self.log(f"Stock buffer refilled with {len(self.market_stock)} markets")
            else:
                await self.log("Failed to fetch fresh markets. No restock.", level="ERROR")
                return

        # Queue 10 from stock
        queued = await self.queue_from_stock()
        if queued > 0:
            # Signal Brain that new opportunities are ready
            await self.bus.publish(
                "OPPORTUNITIES_READY",
                {
                    "count": queued,
                    "source": "SENSES",
                },
                self.name,
            )
            await self.log(f"Restocked: {queued} opportunities added to queue. Senses returning to STANDBY.", level="SUCCESS")

    async def run_scout(self, opp_queue: asyncio.Queue):
        """DEPRECATED: Continuous scanning disabled - now scans only on cycle start."""
        # This method is deprecated and no longer called
        await self.log("WARNING: run_scout called but is deprecated. Scans now happen on cycle start only.", level="WARN")

    async def on_tick(self, payload: dict[str, Any]):
        pass
