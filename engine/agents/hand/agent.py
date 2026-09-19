"""
MEGA-AGENT 4: THE HAND
Role: Tactical Executioner

Core HandAgent class with trade execution capabilities.
"""

from datetime import UTC
from typing import Any

from agents.base import BaseAgent
from core import trading_mode
from core.bus import EventBus
from core.ledger import (
    outcome_from_market,
    record_decision,
    record_fill,
    record_settlement,
    unsettled_fill_tickers,
)
from core.settings import Live
from core.synapse import Synapse
from core.vault import RecursiveVault
from core.vault_utils import check_profit_lock_threshold, publish_vault_state

from .execution import calculate_kelly_stake as exec_calculate_kelly_stake
from .execution import execute_order as exec_execute_order
from .execution import has_open_position as exec_has_open_position
from .execution import parse_orderbook, send_notification
from .execution import snipe_check as exec_snipe_check
from .exits import average_entry_price_cents, evaluate_exit


class HandAgent(BaseAgent):
    """The Tactical Executioner - Precision Strike & Budget Sentinel"""

    # Live: read from core.constants at access time, so a dashboard edit
    # applies to the next order. Tests may still assign an instance override.
    MAX_STAKE_CENTS = Live("HAND_MAX_STAKE_CENTS")
    PROFIT_LOCK_THRESHOLD = Live("VAULT_PROFIT_THRESHOLD_CENTS")

    def __init__(
        self,
        agent_id: int,
        bus: EventBus,
        vault: RecursiveVault,
        kalshi_client=None,
        synapse: Synapse = None,
        error_manager=None,
    ):
        super().__init__("HAND", agent_id, bus, synapse, error_manager)
        self.vault = vault
        self.kalshi_client = kalshi_client

    async def setup(self):
        """Subscribe to execution signals and the cycle-end exit review."""
        await self.log("Hand online. Precision strike capability ready.")
        await self.bus.subscribe("EXECUTION_READY", self.on_execution_ready)
        # Exits are checked once per cycle. Entering a position and never
        # deciding whether to leave it is how a drifting loser becomes a
        # certain one.
        await self.bus.subscribe("CYCLE_END", self.check_exits)
        # Nothing else in the engine ever called record_settlement, so every
        # fill's pnl_cents stayed None forever and calibration() had nothing
        # to measure. Checked on the same cycle boundary as exits.
        await self.bus.subscribe("CYCLE_END", self.settle_positions)

    async def check_exits(self, _message=None) -> int:
        """Review every open position against the exit policy. Returns closures.

        Never raises: this runs on the cycle boundary, and a failure to review
        exits must not take down the cycle that called it.
        """
        if not self.kalshi_client:
            return 0

        # is_live() is already set for this cycle by the time CYCLE_END
        # fires (execute_single_cycle arms it before publishing CYCLE_END),
        # so it tells us which book this review can actually act on.
        #
        # Live: review the real Kalshi account. A ticker held only on paper
        # -- e.g. from an earlier paper soak, replayed by
        # load_paper_positions at boot -- must not be merged in here: it
        # would be evaluated as though it were real exposure, and a
        # paper-only exit would call close_position, which places a real
        # reduce-only sell on Kalshi for contracts the live account may not
        # even hold.
        #
        # Paper: review the paper book only. KalshiClient.place_order
        # simulates every fill while is_live() is False, real position or
        # not, so calling close_position on a *real* Kalshi holding here
        # would not actually sell it -- the position stays open -- while
        # still looking locally like a successful close. Worse, that
        # simulated fill goes through paper_fill same as any other paper
        # order, which would write a phantom short into the paper book for
        # a ticker the paper book never actually bought (a sell with
        # nothing on the other side of it), repeatable every cycle the
        # policy kept tripping on that real position. A real holding is
        # left for a live cycle, the only mode that can actually act on it.
        if trading_mode.is_live():
            try:
                positions = list(await self.kalshi_client.get_positions() or [])
            except Exception as e:
                await self.log(f"Could not read positions for exit review: {e}", level="ERROR")
                positions = []
        else:
            positions = trading_mode.paper_positions()

        closed = 0
        for position in positions:
            ticker = position.get("ticker") or position.get("market_id")
            quantity = position.get("position")
            if not ticker or not quantity:
                continue

            # Kalshi signs the quantity: negative means a NO holding. A NO
            # position gains when the YES price falls, so valuing it as YES
            # would read its stop-loss exactly backwards -- a winning NO
            # position would look like a losing one and be closed.
            side = "no" if int(quantity) < 0 else "yes"

            entry = average_entry_price_cents(position)
            if entry is None:
                await self.log(
                    f"Holding {ticker}: cannot establish entry price, so no exit "
                    "decision can be made on it.",
                    level="WARN",
                )
                continue

            current = await self._current_price_cents(ticker, side)
            if current is None:
                continue

            decision = evaluate_exit(
                entry_price_cents=entry,
                current_price_cents=current,
                hours_to_expiry=self._hours_to_expiry(position),
            )
            if not decision.should_exit:
                continue

            await self.log(f"EXIT {side.upper()} {ticker}: {decision.reason}", level="WARN")
            try:
                result = await self.kalshi_client.close_position(
                    ticker, abs(int(quantity)), side=side
                )
            except Exception as e:
                await self.log(f"Failed to close {ticker}: {e}", level="ERROR")
                continue

            if result:
                closed += 1
                if not trading_mode.is_live():
                    # `current` is the resting bid this decision was made
                    # against -- the real proceeds a sell at this price
                    # would fetch. close_position itself asks for a 1c
                    # marketable limit to guarantee the fill (see
                    # KalshiClient.close_position), so crediting from its
                    # own price argument would credit a cent a contract;
                    # this is the one place that knows what the exit was
                    # actually worth.
                    trading_mode.adjust_paper_cash(current * abs(int(quantity)))
                record_decision(
                    ticker,
                    current / 100.0,
                    outcome="EXITED",
                    veto_reason=decision.reason,
                )
                await self.bus.publish(
                    "POSITION_CLOSED",
                    {"ticker": ticker, "reason": decision.reason, "price": current},
                    self.name,
                )

        return closed

    async def settle_positions(self, _message=None) -> int:
        """Look up the outcome of every ticker with an unsettled fill.

        Nothing else in the engine calls record_settlement in production, so
        without this every fill's pnl_cents stayed None forever, calibration()
        had nothing to measure, and realised_edge() reported n=0 no matter how
        long a paper soak ran. Never raises: a settlement check runs on the
        cycle boundary and must not be able to take the cycle down with it.
        """
        if not self.kalshi_client:
            return 0

        settled = 0
        for ticker in unsettled_fill_tickers():
            try:
                market = await self.kalshi_client.get_market(ticker)
            except Exception as e:
                await self.log(f"Could not check settlement for {ticker}: {e}", level="ERROR")
                continue
            if not market:
                continue

            outcome = outcome_from_market(market)
            if outcome is None:
                continue

            record_settlement(ticker, outcome)
            settled += 1
            await self.log(f"SETTLED {ticker}: {'YES' if outcome else 'NO'}")

            # A settled market cannot be traded again. Paper fills never reach
            # Kalshi's own portfolio, so the paper book is the only place that
            # would otherwise go on believing this ticker is still held --
            # has_open_position would refuse to re-enter a market that no
            # longer exists, and check_exits would keep polling a dead book
            # forever.
            #
            # settle_paper_position reports what the winning side (if any)
            # pays in cents; crediting it is what makes a paper win actually
            # grow the paper bankroll rather than just deleting the holding.
            payout = trading_mode.settle_paper_position(ticker, outcome)
            trading_mode.adjust_paper_cash(payout)

        return settled

    async def _current_price_cents(self, ticker: str, side: str = "yes") -> int | None:
        """What closing the held side would fetch right now, in cents.

        Closing a position is a sell, and a seller receives the best resting
        bid on their own side, not an ask -- Kalshi quotes one book and no
        explicit asks at all (CLAUDE.md: "the orderbook has no asks").
        parse_orderbook is the one place that knows the book's real shapes;
        reading a literal "asks" key here read every real response as empty
        and made check_exits a no-op for every position, in paper and live,
        even once CYCLE_END was wired to call it.
        """
        try:
            raw = await self.kalshi_client.get_orderbook(ticker)
        except Exception:
            return None

        book = parse_orderbook(raw, side=side)
        return book["best_bid"] if book else None

    @staticmethod
    def _hours_to_expiry(position: dict) -> float | None:
        """Hours until settlement, or None when the row does not say."""
        from datetime import datetime

        raw = position.get("expiration_time") or position.get("expiration")
        if not raw:
            return None
        try:
            expiry = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return None
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=UTC)
        return (expiry - datetime.now(UTC)).total_seconds() / 3600.0

    async def on_execution_ready(self, message):
        """Execute approved trade from Brain > Synapse (Primary) or Brain Ref (Legacy)"""
        await self.log("Execution signal received. Initiating strike sequence...")

        target = None

        # 1. Synapse Flow (Decoupled)
        if self.synapse:
            try:
                signal_model = await self.synapse.executions.pop()
                if signal_model:
                    await self.log(f"Synapse Signal: {signal_model.target_opportunity.ticker}")

                    # Map to Legacy Target Format for downstream methods
                    target = {
                        "ticker": signal_model.target_opportunity.ticker,
                        "confidence": signal_model.confidence,
                        "ev": signal_model.monte_carlo_ev,
                        "estimated_probability": signal_model.estimated_probability,
                        "side": (signal_model.side or "YES").lower(),
                        "side_price": signal_model.side_price,
                        "side_probability": signal_model.side_probability,
                        "reasoning": signal_model.reasoning,
                        "suggested_size": signal_model.suggested_count,
                        "market_data": signal_model.target_opportunity.market_data.raw_response,
                    }
            except Exception as e:
                await self.log(f"Synapse Pop (Execution) Error: {e}", level="ERROR")
                await self.bus.publish(
                    "SYSTEM_FATAL", {"message": f"Hand Agent Failed: {e!s}"}, self.name
                )

        if not target:
            return

        ticker = target.get("ticker", "UNKNOWN")
        confidence = target.get("confidence", 0)
        ev = target.get("ev", 0)

        await self.log(f"Target acquired: {ticker}")

        # 0. Refuse to stack into a market we already hold.
        if await exec_has_open_position(self.kalshi_client, ticker):
            await self.log(
                f"Already holding {ticker} - skipping to avoid concentrating exposure.",
                level="WARN",
            )
            return

        side = target.get("side", "yes")

        # 1. Snipe Check (Order Book Analysis)
        snipe_result = await exec_snipe_check(
            self.kalshi_client, ticker, self.log, self.MAX_STAKE_CENTS, side=side
        )
        if not snipe_result.get("valid"):
            await self.log(f"Snipe check failed: {snipe_result.get('reason')}", level="ERROR")
            return

        entry_price = snipe_result.get("entry_price", 50)

        # 2. Kelly Sizing, against the price actually available in the book.
        # side_probability is the probability of the side being bought: for NO
        # that is (1 - p), which is what Kelly needs.
        probability = target.get("side_probability")
        if probability is None:
            probability = target.get("estimated_probability")
        stake = exec_calculate_kelly_stake(
            confidence,
            ev,
            self.vault,
            self.MAX_STAKE_CENTS,
            probability=probability,
            price_cents=entry_price,
        )
        if stake <= 0:
            await self.log(
                f"No stake for {ticker}: edge {ev:+.3f} at {entry_price}c "
                f"(p={probability}) does not justify a position.",
                level="WARN",
            )
            return
        await self.log(
            f"Kelly sizing: ${stake/100:.2f} "
            f"({side.upper()} p={probability:.2f} @ {entry_price}c, edge {ev:+.3f})"
        )

        # 3. Execute Order
        order_result = await exec_execute_order(
            kalshi_client=self.kalshi_client,
            vault=self.vault,
            ticker=ticker,
            price=entry_price,
            stake=stake,
            max_stake_cents=self.MAX_STAKE_CENTS,
            log_callback=self.log,
            side=side,
        )

        if order_result.get("success"):
            # What filled, not what was asked for: an immediate-or-cancel
            # order can fill partly.
            stake = order_result.get("stake", stake)
            await self.log(
                f"ORDER EXECUTED: {side.upper()} {ticker} @ {entry_price}¢ for ${stake/100:.2f}"
            )
            # side and entry_price came off the book this order actually
            # crossed, not parsed back out of an order id after the fact --
            # the only way a real Kalshi order id (which carries none of
            # this) can be told apart from a paper one bought at the other
            # side's price.
            record_fill(
                ticker,
                stake,
                order_result.get("order_id"),
                side=side,
                price_cents=entry_price,
                count=stake // entry_price if entry_price else None,
            )

            # 4. Check for Vault Lock
            should_lock, _current_profit = check_profit_lock_threshold(
                self.vault, self.PROFIT_LOCK_THRESHOLD
            )
            if should_lock:
                # is_live() already reflects this cycle's mode by the time a
                # fill reaches here (execute_single_cycle arms it before
                # publishing the events that lead to this); the vault latches
                # the lock per mode, see RecursiveVault.lock_principal.
                self.vault.lock_principal(is_paper_trading=not trading_mode.is_live())
                await self.log("VAULT LOCKED: $300 principal secured. Trading house money!")

            # 5. Send Notification
            await send_notification(ticker, stake, order_result, self.log)

            # Publish trade result for Soul to learn
            await self.bus.publish(
                "TRADE_RESULT",
                {
                    "outcome": "pending",
                    "ticker": ticker,
                    "stake": stake,
                    "entry_price": entry_price,
                    "details": f"{ticker} at {entry_price}¢",
                },
                self.name,
            )
        else:
            await self.log(f"ORDER FAILED: {order_result.get('error')}", level="ERROR")

    # Instance method wrappers for test compatibility
    async def execute_order(self, ticker: str, price: int, stake: int) -> dict:
        """Execute an order - instance method wrapper for tests."""
        return await exec_execute_order(
            kalshi_client=self.kalshi_client,
            vault=self.vault,
            ticker=ticker,
            price=price,
            stake=stake,
            max_stake_cents=self.MAX_STAKE_CENTS,
            log_callback=self.log,
        )

    def calculate_kelly_stake(
        self,
        confidence: float,
        ev: float,
        probability: float | None = None,
        price_cents: int | None = None,
    ) -> int:
        """Size a position. Thin wrapper over the execution module."""
        return exec_calculate_kelly_stake(
            confidence,
            ev,
            self.vault,
            self.MAX_STAKE_CENTS,
            probability=probability,
            price_cents=price_cents,
        )

    async def snipe_check(self, ticker: str) -> dict:
        """Perform snipe check - instance method wrapper for tests."""
        return await exec_snipe_check(self.kalshi_client, ticker, self.log, self.MAX_STAKE_CENTS)

    async def on_tick(self, payload: dict[str, Any]):
        """Periodic vault state broadcast"""
        await publish_vault_state(self.bus, self.vault, self.name)
