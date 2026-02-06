"""
MEGA-AGENT 4: THE HAND
Role: Tactical Executioner

Core HandAgent class with trade execution capabilities.
"""
from typing import Any

from agents.base import BaseAgent
from core.bus import EventBus
from core.constants import HAND_MAX_STAKE_CENTS, HAND_PROFIT_LOCK_THRESHOLD
from core.synapse import Synapse
from core.vault import RecursiveVault
from core.vault_utils import check_profit_lock_threshold, publish_vault_state

from .execution import (
    snipe_check as exec_snipe_check,
    calculate_kelly_stake as exec_calculate_kelly_stake,
    execute_order as exec_execute_order,
    send_notification
)


class HandAgent(BaseAgent):
    """The Tactical Executioner - Precision Strike & Budget Sentinel"""

    MAX_STAKE_CENTS = HAND_MAX_STAKE_CENTS
    PROFIT_LOCK_THRESHOLD = HAND_PROFIT_LOCK_THRESHOLD

    def __init__(
        self,
        agent_id: int,
        bus: EventBus,
        vault: RecursiveVault,
        brain_agent=None,
        kalshi_client=None,
        synapse: Synapse = None,
    ):
        super().__init__("HAND", agent_id, bus, synapse)
        self.vault = vault
        self.brain = brain_agent
        self.kalshi_client = kalshi_client
        self.pending_orders = []

    async def setup(self):
        await self.log("Hand online. Precision strike capability ready.")
        await self.bus.subscribe("EXECUTION_READY", self.on_execution_ready)

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
                        "reasoning": signal_model.reasoning,
                        "suggested_size": signal_model.suggested_count,
                        "market_data": signal_model.target_opportunity.market_data.raw_response
                    }
            except Exception as e:
                await self.log(f"Synapse Pop (Execution) Error: {e}", level="ERROR")
                await self.bus.publish("SYSTEM_FATAL", {"message": f"Hand Agent Failed: {e!s}"}, self.name)

        if not target:
            return

        ticker = target.get("ticker", "UNKNOWN")
        confidence = target.get("confidence", 0)
        ev = target.get("ev", 0)

        await self.log(f"Target acquired: {ticker}")

        # 1. Snipe Check (Order Book Analysis)
        snipe_result = await exec_snipe_check(self.kalshi_client, ticker, self.log, self.MAX_STAKE_CENTS)
        if not snipe_result.get("valid"):
            await self.log(f"Snipe check failed: {snipe_result.get('reason')}", level="ERROR")
            return

        entry_price = snipe_result.get("entry_price", 50)

        # 2. Kelly Sizing
        stake = exec_calculate_kelly_stake(confidence, ev, self.vault, self.MAX_STAKE_CENTS)
        await self.log(f"Kelly sizing: ${stake/100:.2f} (Confidence: {confidence*100:.1f}%)")

        # 3. Execute Order
        order_result = await exec_execute_order(
            kalshi_client=self.kalshi_client,
            vault=self.vault,
            ticker=ticker,
            price=entry_price,
            stake=stake,
            max_stake_cents=self.MAX_STAKE_CENTS,
            log_callback=self.log
        )

        if order_result.get("success"):
            await self.log(f"ORDER EXECUTED: {ticker} @ {entry_price}¢ for ${stake/100:.2f}")

            # 4. Check for Vault Lock
            should_lock, current_profit = check_profit_lock_threshold(self.vault, self.PROFIT_LOCK_THRESHOLD)
            if should_lock:
                self.vault.lock_principal()
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
            log_callback=self.log
        )

    def calculate_kelly_stake(self, confidence: float, ev: float) -> int:
        """Calculate Kelly stake - instance method wrapper for tests."""
        return exec_calculate_kelly_stake(confidence, ev, self.vault, self.MAX_STAKE_CENTS)

    async def snipe_check(self, ticker: str) -> dict:
        """Perform snipe check - instance method wrapper for tests."""
        return await exec_snipe_check(self.kalshi_client, ticker, self.log, self.MAX_STAKE_CENTS)

    async def on_tick(self, payload: dict[str, Any]):
        """Periodic vault state broadcast"""
        await publish_vault_state(self.bus, self.vault, self.name)
