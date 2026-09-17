"""
MEGA-AGENT 2: THE SENSES
Role: 24/7 Passive Observer

Core SensesAgent class with market scanning capabilities.
"""
import asyncio
import time
import os
from typing import Any

from agents.base import BaseAgent
from core.bus import EventBus
from core.constants import (
    SENSES_MIN_LIQUIDITY,
    SENSES_QUEUE_BATCH_SIZE,
    SENSES_STOCK_BUFFER_SIZE,
)
from core.db import log_to_db
from core.flow_control import check_execution_queue_limit, check_opportunity_queue_limit
from core.synapse import MarketData, Opportunity, Synapse

from .scanner import fetch_kalshi_markets, queue_from_stock, surveillance_loop


class SensesAgent(BaseAgent):
    """The 24/7 Observer - Surveillance & Signal Detection"""

    MIN_LIQUIDITY = SENSES_MIN_LIQUIDITY
    STOCK_BUFFER_SIZE = SENSES_STOCK_BUFFER_SIZE
    QUEUE_BATCH_SIZE = SENSES_QUEUE_BATCH_SIZE
    RESTOCK_THRESHOLD = 5

    def __init__(self, agent_id: int, bus: EventBus, kalshi_client=None, synapse: Synapse = None, error_manager=None):
        super().__init__("SENSES", agent_id, bus, synapse, error_manager)
        self.kalshi_client = kalshi_client
        self.opportunity_queue: list[dict] = []
        self.is_scanning = False

        # Stock buffer: Keep markets in memory, queue top batch
        self.market_stock: list[dict] = []
        self._initial_scan_done = False
        self._dumped_count = 0

    async def fetch_market_context(self, ticker: str, title: str) -> list[str]:
        """Fetch external context (news) for a market"""
        try:
            from ddgs import DDGS

            # Run simple search with timeout
            query = f"{title} news"
            loop = asyncio.get_event_loop()

            results = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: list(DDGS(proxy=None).text(query, max_results=3))
                ),
                timeout=10.0
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
        if self._initial_scan_done:
            await self.log("Initial scan already complete. Senses in STANDBY mode.", level="INFO")
            return

        self.is_scanning = True
        self._initial_scan_done = True
        await self.log("Initiating passive market scan (zero token cost)...")

        await surveillance_loop(
            senses_agent=self,
            stock_buffer_size=self.STOCK_BUFFER_SIZE,
            queue_batch_size=self.QUEUE_BATCH_SIZE,
            log_callback=self.log,
            log_error_callback=self.log_error,
            bus=self.bus
        )
        await self.log("Initial scan complete. Senses entering STANDBY mode.", level="SUCCESS")

    async def stop_scan(self, message):
        """Stop scanning at cycle end"""
        self.is_scanning = False
        await self.log("Surveillance paused. Cycle complete.")

    # How long a ticker stays excluded from re-queueing after it was queued.
    # Session-scoped and time-bounded: a market vetoed at 09:00 may deserve a
    # fresh look hours later, but not on the very next restock. Restart
    # forgets this; the Hand's position guard is what survives a restart.
    REQUEUE_AFTER_SECONDS = float(os.getenv("SENSES_REQUEUE_AFTER_SECONDS", "21600"))

    def _queued_at(self) -> dict[str, float]:
        if not hasattr(self, "_queued_at_map"):
            self._queued_at_map: dict[str, float] = {}
        return self._queued_at_map

    def mark_queued(self, ticker: str) -> None:
        """Remember that `ticker` was queued now."""
        self._queued_at()[ticker] = time.time()

    def recently_queued(self) -> frozenset[str]:
        """Tickers queued within REQUEUE_AFTER_SECONDS. Expired ones drop out."""
        cutoff = time.time() - self.REQUEUE_AFTER_SECONDS
        live = self._queued_at()
        for t in [t for t, at in live.items() if at < cutoff]:
            del live[t]
        return frozenset(live)

    async def queue_opportunity(self, opportunity: dict):
        """Add opportunity to Synapse queue (primary) and legacy queue (fallback)"""
        ticker = opportunity.get("ticker", "UNKNOWN")
        self.mark_queued(ticker)
        volume = opportunity.get("volume", 0)

        # Synapse Integration (Primary Queue)
        synapse_success = False
        if self.synapse:
            try:
                m_data = opportunity.get("market_data", {})

                market_payload = MarketData(
                    ticker=ticker,
                    title=m_data.get("title", "Unknown"),
                    subtitle=m_data.get("subtitle", ""),
                    yes_price=int(opportunity.get("kalshi_price", 0) * 100),
                    no_price=m_data.get("no_price", 0),
                    volume=int(m_data.get("volume", 0)),
                    expiration=m_data.get("expiration_time", ""),
                    raw_response=m_data
                )

                opp_model = Opportunity(
                    ticker=ticker,
                    market_data=market_payload,
                    source="SENSES",
                )

                await self.synapse.opportunities.push(opp_model)

                queue_size = await self.synapse.opportunities.size()
                await self.log(f"[OK] Queued to Synapse: {ticker} (Queue Size: {queue_size}) | Volume: {volume}")
                synapse_success = True

            except Exception as e:
                await self.log(f"[FAIL] Synapse Push Failed for {ticker}: {e}", level="ERROR")
                synapse_success = False

    #     # Legacy Flow (Fallback)
    #     if not synapse_success or not self.synapse:
    #         signal_package = {
    #             "market_id": ticker,
    #             "source": opportunity.get("source", "Kalshi"),
    #             "gap_delta": 0,
    #             "pinnacle_odds": 0,
    #             "kalshi_price": opportunity.get("kalshi_price", 0),
    #             "status": "QUEUED",
    #             "market_data": opportunity.get("market_data", {})
    #         }
    #         self.opportunity_queue.append(opportunity)
    #         await log_to_db("opportunity_queue", signal_package)
    #         await self.log(f"[WARN] Fallback to Legacy Queue: {ticker} | Volume: {volume}", level="WARN")

    # def pop_opportunity(self) -> dict | None:
    #     """Get next opportunity for Brain"""
    #     return self.opportunity_queue.pop(0) if self.opportunity_queue else None

    async def on_restock_request(self, message):
        """Handle restock request from Brain"""
        await self.log("Restock request received from Brain")

        # FLOW CONTROL: Don't add more if opportunity queue is already large
        if self.synapse:
            is_at_limit, opp_queue_size = await check_opportunity_queue_limit(self.synapse)
            if is_at_limit:
                await self.log(f"Flow Control: Opportunity queue still has {opp_queue_size} items. Skipping restock.", level="WARN")
                return

        # FLOW CONTROL: Check execution queue
        if self.synapse:
            is_at_limit, exec_size = await check_execution_queue_limit(self.synapse)
            if is_at_limit:
                await self.log(f"Flow Control: Execution queue at limit ({exec_size}/10). Skipping restock.", level="WARN")
                return

        # If stock is low, pull fresh from Kalshi
        if len(self.market_stock) < self.QUEUE_BATCH_SIZE:
            await self.log("Stock buffer low. Fetching fresh markets from Kalshi...")
            # fetch_kalshi_markets already filters, sorts by volume and
            # truncates. Re-sorting here on "volume" -- a key Kalshi no
            # longer sends -- scored every market as 0 and undid the order.
            markets = await fetch_kalshi_markets(
                self.kalshi_client, self.log, needed=self.STOCK_BUFFER_SIZE,
                exclude=self.recently_queued(),
            )
            if markets:
                self.market_stock = markets
                await self.log(f"Stock buffer refilled with {len(self.market_stock)} markets")
            else:
                await self.log("Failed to fetch fresh markets. No restock.", level="ERROR")
                return

        # Queue from stock
        queued = await queue_from_stock(
            market_stock=self.market_stock,
            queue_batch_size=self.QUEUE_BATCH_SIZE,
            synapse=self.synapse,
            log_callback=self.log,
            fetch_context_callback=self.fetch_market_context,
            queue_opportunity_callback=self.queue_opportunity
        )

        if queued > 0:
            await self.bus.publish(
                "OPPORTUNITIES_READY",
                {"count": queued, "source": "SENSES"},
                self.name,
            )
            await self.log(f"Restocked: {queued} opportunities. Senses returning to STANDBY.", level="SUCCESS")

    async def run_scout(self, opp_queue: asyncio.Queue):
        """DEPRECATED: Continuous scanning disabled"""
        await self.log("WARNING: run_scout called but is deprecated.", level="WARN")

    async def surveillance_loop(self):
        """Main surveillance loop - wrapper for scanner.surveillance_loop"""
        from .scanner import surveillance_loop as scanner_surveillance_loop

        await scanner_surveillance_loop(
            senses_agent=self,
            stock_buffer_size=self.STOCK_BUFFER_SIZE,
            queue_batch_size=self.QUEUE_BATCH_SIZE,
            log_callback=self.log,
            log_error_callback=self.log,
            bus=self.bus
        )

    async def on_tick(self, payload: dict[str, Any]):
        pass
