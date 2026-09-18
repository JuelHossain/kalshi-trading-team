"""
MEGA-AGENT 2: THE SENSES
Role: 24/7 Passive Observer

Core SensesAgent class with market scanning capabilities.
"""

import time
from typing import Any

from agents.base import BaseAgent
from core import constants
from core.bus import EventBus
from core.flow_control import check_execution_queue_limit, check_opportunity_queue_limit
from core.settings import Live
from core.synapse import MarketData, Opportunity, Synapse

from .scanner import fetch_kalshi_markets, queue_from_stock, surveillance_loop


class SensesAgent(BaseAgent):
    """The 24/7 Observer - Surveillance & Signal Detection"""

    # Live: read from core.constants at access time, so a dashboard edit
    # applies to the next scan. Tests may still assign an instance override.
    STOCK_BUFFER_SIZE = Live("SENSES_STOCK_BUFFER_SIZE")
    QUEUE_BATCH_SIZE = Live("SENSES_QUEUE_BATCH_SIZE")
    REQUEUE_AFTER_SECONDS = Live("SENSES_REQUEUE_AFTER_SECONDS")
    RESCAN_COOLDOWN_SECONDS = Live("SENSES_RESCAN_COOLDOWN_SECONDS")

    def __init__(
        self,
        agent_id: int,
        bus: EventBus,
        kalshi_client=None,
        synapse: Synapse = None,
        error_manager=None,
    ):
        super().__init__("SENSES", agent_id, bus, synapse, error_manager)
        self.kalshi_client = kalshi_client

        # Stock buffer: Keep markets in memory, queue top batch
        self.market_stock: list[dict] = []
        self._initial_scan_done = False
        self._dumped_count = 0
        self._last_scan_attempt_time = 0.0

    async def setup(self):
        """Subscribe to pre-flight completion and restock requests."""
        await self.log("Senses online. 24/7 passive surveillance activated.")
        await self.bus.subscribe("PREFLIGHT_COMPLETE", self.start_scan)
        await self.bus.subscribe("CYCLE_END", self.stop_scan)
        await self.bus.subscribe("REQUEST_RESTOCK", self.on_restock_request)

    async def start_scan(self, message):
        """Begin passive market surveillance, or rescan a Senses stuck empty.

        The first PREFLIGHT_COMPLETE (published every cycle) runs the full
        scan; every one after that is normally a no-op, which is what keeps
        a healthy stock buffer from being re-fetched every 30s.

        But if a scan -- the first one, or a later restock -- ever leaves
        both the stock buffer and the opportunity queue empty, standing pat
        is a deadlock, not patience: REQUEST_RESTOCK is the only other route
        into a scan, and the Brain only sends it after enough vetoes, which
        needs an opportunity queue that will now never have anything in it.
        Confirmed live 2026-09-18: the first scan found 0 markets and the
        engine ran ~500 cycles analysing nothing, reporting healthy the
        whole time. A cooldown keeps this from re-walking Kalshi's listing
        every cycle while it stays empty.
        """
        if not self._initial_scan_done:
            self._initial_scan_done = True
            await self.log("Initiating passive market scan (zero token cost)...")
            await self._scan()
            return

        if await self._should_rescan():
            await self.log(
                "Scan left nothing queued and the cooldown has passed; rescanning.",
                level="INFO",
            )
            await self._scan()
            return

        await self.log("Initial scan already complete. Senses in STANDBY mode.", level="INFO")

    async def _should_rescan(self) -> bool:
        """Whether a Senses that has already scanned should scan again now."""
        if self.market_stock:
            return False  # unqueued stock on hand; no need to hit Kalshi
        if self.synapse and await self.synapse.opportunities.size() > 0:
            return False  # Brain still has work; scanning now would just pile on
        return (time.time() - self._last_scan_attempt_time) >= self.RESCAN_COOLDOWN_SECONDS

    async def _scan(self):
        """Run one surveillance pass and record when it was attempted."""
        self._last_scan_attempt_time = time.time()
        await surveillance_loop(
            senses_agent=self,
            stock_buffer_size=self.STOCK_BUFFER_SIZE,
            queue_batch_size=self.QUEUE_BATCH_SIZE,
            log_callback=self.log,
            log_error_callback=self.log_error,
            bus=self.bus,
        )
        await self.log("Scan complete. Senses entering STANDBY mode.", level="SUCCESS")

    async def stop_scan(self, message):
        """Stop scanning at cycle end"""
        await self.log("Surveillance paused. Cycle complete.")

    # Requeue exclusion is session-scoped and time-bounded: a market vetoed at
    # 09:00 may deserve a fresh look hours later, but not on the very next
    # restock. Restart forgets this; the Hand's position guard survives one.

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
        """Push one opportunity onto the Synapse queue for the Brain."""
        ticker = opportunity.get("ticker", "UNKNOWN")
        self.mark_queued(ticker)
        volume = opportunity.get("volume", 0)

        # Synapse Integration (Primary Queue)
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
                    raw_response=m_data,
                )

                opp_model = Opportunity(
                    ticker=ticker,
                    market_data=market_payload,
                    source="SENSES",
                )

                await self.synapse.opportunities.push(opp_model)

                queue_size = await self.synapse.opportunities.size()
                await self.log(
                    f"[OK] Queued to Synapse: {ticker} (Queue Size: {queue_size}) | Volume: {volume}"
                )

            except Exception as e:
                await self.log(f"[FAIL] Synapse Push Failed for {ticker}: {e}", level="ERROR")

    async def on_restock_request(self, message):
        """Handle restock request from Brain"""
        await self.log("Restock request received from Brain")

        # FLOW CONTROL: Don't add more if opportunity queue is already large
        if self.synapse:
            is_at_limit, opp_queue_size = await check_opportunity_queue_limit(self.synapse)
            if is_at_limit:
                await self.log(
                    f"Flow Control: Opportunity queue still has {opp_queue_size} items. Skipping restock.",
                    level="WARN",
                )
                return

        # FLOW CONTROL: Check execution queue
        if self.synapse:
            is_at_limit, exec_size = await check_execution_queue_limit(self.synapse)
            if is_at_limit:
                await self.log(
                    f"Flow Control: Execution queue at limit ({exec_size}/{constants.MAX_EXECUTION_QUEUE_SIZE}). Skipping restock.",
                    level="WARN",
                )
                return

        # If stock is low, pull fresh from Kalshi
        if len(self.market_stock) < self.QUEUE_BATCH_SIZE:
            await self.log("Stock buffer low. Fetching fresh markets from Kalshi...")
            # Shared with the PREFLIGHT_COMPLETE rescan path (start_scan /
            # _should_rescan) so the two do not hammer Kalshi back-to-back
            # when both see an empty stock buffer.
            self._last_scan_attempt_time = time.time()
            # fetch_kalshi_markets already filters, sorts by volume and
            # truncates. Re-sorting here on "volume" -- a key Kalshi no
            # longer sends -- scored every market as 0 and undid the order.
            markets = await fetch_kalshi_markets(
                self.kalshi_client,
                self.log,
                needed=self.STOCK_BUFFER_SIZE,
                exclude=self.recently_queued(),
            )
            if markets:
                self.market_stock = markets
                await self.log(f"Stock buffer refilled with {len(self.market_stock)} markets")
            else:
                # An empty result is usually "nothing new": every tradeable
                # market in the close window was queued recently. A real
                # fetch failure is already logged at ERROR by the scanner.
                await self.log(
                    "No new tradeable markets to queue; buffer stays empty.", level="WARN"
                )
                return

        # Queue from stock
        queued = await queue_from_stock(
            market_stock=self.market_stock,
            queue_batch_size=self.QUEUE_BATCH_SIZE,
            synapse=self.synapse,
            log_callback=self.log,
            queue_opportunity_callback=self.queue_opportunity,
        )

        if queued > 0:
            await self.bus.publish(
                "OPPORTUNITIES_READY",
                {"count": queued, "source": "SENSES"},
                self.name,
            )
            await self.log(
                f"Restocked: {queued} opportunities. Senses returning to STANDBY.", level="SUCCESS"
            )

    async def surveillance_loop(self):
        """Main surveillance loop - wrapper for scanner.surveillance_loop"""
        from .scanner import surveillance_loop as scanner_surveillance_loop

        await scanner_surveillance_loop(
            senses_agent=self,
            stock_buffer_size=self.STOCK_BUFFER_SIZE,
            queue_batch_size=self.QUEUE_BATCH_SIZE,
            log_callback=self.log,
            log_error_callback=self.log,
            bus=self.bus,
        )

    async def on_tick(self, payload: dict[str, Any]):
        """Senses scans on request, not on ticks."""
