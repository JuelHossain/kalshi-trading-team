"""
MEGA-AGENT 4: THE HAND
Role: Tactical Executioner

Workflow:
1. Snipe Check: Scan Kalshi v2 Order Book for best entry (zero slippage)
2. Kelly Sizing: Calculate exact stake (Max $75 per trade)
3. Execution: Place Limit Order on Kalshi v2
4. Vault Lock: Lock $300 principal when profit > $50
5. Notification: Send high-priority alert via ntfy.sh
"""

import os
from typing import Any

import aiohttp
from agents.base import BaseAgent
from core.bus import EventBus
from core.synapse import Synapse
from core.vault import RecursiveVault


class HandAgent(BaseAgent):
    """The Tactical Executioner - Precision Strike & Budget Sentinel"""

    MAX_STAKE_CENTS = 7500  # $75 max per trade
    PROFIT_LOCK_THRESHOLD = 5000  # $50 profit triggers principal lock
    NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "kalshi-alerts")

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
                    await self.log(f"✋ Synapse Signal: {signal_model.target_opportunity.ticker}")
                    
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

        # 2. Legacy Fallback (Direct Reference)
        if not target and self.brain:
            target = self.brain.pop_execution_target()

        if not target:
            await self.log("No execution target available.")
            return

        ticker = target.get("ticker", "UNKNOWN")
        confidence = target.get("confidence", 0)
        ev = target.get("ev", 0)

        await self.log(f"Target acquired: {ticker}")

        # 1. Snipe Check (Order Book Analysis)
        snipe_result = await self.snipe_check(ticker)
        if not snipe_result.get("valid"):
            await self.log(f"Snipe check failed: {snipe_result.get('reason')}", level="ERROR")
            return

        entry_price = snipe_result.get("entry_price", 50)

        # 2. Kelly Sizing
        stake = self.calculate_kelly_stake(confidence, ev)
        await self.log(f"Kelly sizing: ${stake/100:.2f} (Confidence: {confidence*100:.1f}%)")

        # 3. Execute Order
        order_result = await self.execute_order(ticker, entry_price, stake)

        if order_result.get("success"):
            await self.log(f"✅ ORDER EXECUTED: {ticker} @ {entry_price}¢ for ${stake/100:.2f}")

            # 4. Check for Vault Lock
            current_profit = self.vault.current_balance - self.vault.start_of_day_balance
            if current_profit >= self.PROFIT_LOCK_THRESHOLD and not self.vault.is_locked:
                self.vault.lock_principal()
                await self.log("🔒 VAULT LOCKED: $300 principal secured. Trading house money!")

            # 5. Send Notification
            await self.send_notification(ticker, stake, order_result)

            # Publish trade result for Soul to learn
            await self.bus.publish(
                "TRADE_RESULT",
                {
                    "outcome": "pending",  # Will update on settlement
                    "ticker": ticker,
                    "stake": stake,
                    "entry_price": entry_price,
                    "details": f"{ticker} at {entry_price}¢",
                },
                self.name,
            )
        else:
            await self.log(f"❌ ORDER FAILED: {order_result.get('error')}", level="ERROR")

    async def snipe_check(self, ticker: str) -> dict:
        """Analyze order book for best entry with zero slippage"""
        if not self.kalshi_client:
            await self.log("Kalshi client unavailable. Simulating snipe check.")
            return {"valid": True, "entry_price": 50, "slippage": 0}

        try:
            orderbook = await self.kalshi_client.get_orderbook(ticker)

            # Find best bid/ask spread
            best_bid = orderbook.get("bids", [{}])[0].get("price", 45)
            best_ask = orderbook.get("asks", [{}])[0].get("price", 55)
            spread = best_ask - best_bid

            if spread > 5:  # More than 5¢ spread = potential slippage
                return {
                    "valid": False,
                    "reason": f"Spread too wide: {spread}¢",
                    "entry_price": best_ask,
                }

            return {"valid": True, "entry_price": best_ask, "slippage": 0, "spread": spread}
        except Exception as e:
            return {"valid": False, "reason": str(e)[:50]}

    def calculate_kelly_stake(self, confidence: float, ev: float) -> int:
        """Kelly Criterion with conservative factor"""
        # Kelly formula: f = (bp - q) / b
        # Where b = odds, p = win probability, q = lose probability

        if ev <= 0:
            return 0

        # Simplified Kelly with 25% fraction (quarter Kelly for safety)
        kelly_fraction = max(0, (confidence - 0.5) * 0.5) * 0.25

        # Calculate stake in cents
        available = min(self.vault.current_balance, self.MAX_STAKE_CENTS)
        stake = int(available * kelly_fraction)

        # Cap at max stake
        return min(stake, self.MAX_STAKE_CENTS)

    async def execute_order(self, ticker: str, price: int, stake: int) -> dict:
        """Place limit order on Kalshi v2 with comprehensive pre-trade validation."""

        # === PRE-TRADE VALIDATION ===

        # 1. Check kill switch
        if self.vault.kill_switch_active:
            return {"success": False, "error": "Kill switch active - trading halted"}

        # 2. Validate ticker format (basic sanity check)
        if not ticker or not isinstance(ticker, str) or len(ticker) < 3:
            return {"success": False, "error": f"Invalid ticker format: {ticker}"}

        # 3. Validate price range (Kalshi: 1-99 cents)
        if not isinstance(price, int) or price < 1 or price > 99:
            return {"success": False, "error": f"Price must be 1-99 cents, got: {price}"}

        # 4. Validate stake
        if not isinstance(stake, int) or stake <= 0:
            return {"success": False, "error": f"Stake must be positive integer, got: {stake}"}

        if stake > self.MAX_STAKE_CENTS:
            return {"success": False, "error": f"Stake ${stake/100:.2f} exceeds max ${self.MAX_STAKE_CENTS/100:.2f}"}

        # 5. Check available balance (including reserved funds)
        available_balance = self.vault.get_available_balance()
        if available_balance < stake:
            return {
                "success": False,
                "error": f"Insufficient funds: available=${available_balance/100:.2f}, required=${stake/100:.2f}"
            }

        # 6. Check hard floor (emergency stop if balance drops too low)
        if self.vault.current_balance < 25500:  # $255 hard floor
            return {"success": False, "error": "Hard floor breach - emergency lockdown active"}

        # === SIMULATION MODE ===
        if not self.kalshi_client:
            await self.log("Kalshi client unavailable. Simulating order.")
            # Use atomic balance reservation
            if not self.vault.reserve_funds(stake):
                return {"success": False, "error": "Failed to reserve funds for simulation"}
            # In simulation, we immediately confirm the reservation as spent
            self.vault.confirm_reservation(stake)
            return {"success": True, "order_id": "SIM-001", "simulated": True}

        # === LIVE TRADING ===
        # Calculate contract count
        contract_count = stake // price
        if contract_count <= 0:
            return {"success": False, "error": f"Stake ${stake/100:.2f} too small for price {price}¢"}

        # Reserve funds atomically before placing order
        if not self.vault.reserve_funds(stake):
            return {"success": False, "error": "Failed to reserve funds"}

        try:
            result = await self.kalshi_client.place_order(
                ticker=ticker,
                side="yes",
                type="limit",
                price=price,
                count=contract_count,
            )

            # Order placed successfully - confirm the reservation
            self.vault.confirm_reservation(stake)
            return {"success": True, "order_id": result.get("order_id")}

        except Exception as e:
            # Order failed - release the reserved funds
            self.vault.release_reservation(stake)
            return {"success": False, "error": str(e)[:100]}

    async def send_notification(self, ticker: str, stake: int, result: dict):
        """Send push notification via ntfy.sh"""
        if not self.NTFY_TOPIC:
            return

        try:
            async with aiohttp.ClientSession() as session:
                message = f"🎯 Trade Executed: {ticker}\nStake: ${stake/100:.2f}\nOrder: {result.get('order_id', 'N/A')}"
                await session.post(
                    f"https://ntfy.sh/{self.NTFY_TOPIC}",
                    data=message.encode(),
                    headers={
                        "Title": "Kalshi Trade Alert",
                        "Priority": "high",
                        "Tags": "money_with_wings",
                    },
                )
                await self.log("Push notification sent.")
        except Exception as e:
            await self.log(f"Notification failed: {str(e)[:30]}", level="ERROR")


    async def on_tick(self, payload: dict[str, Any]):
        """Periodic vault state broadcast"""
        # Emit vault update for UI
        await self.bus.publish(
            "VAULT_UPDATE",
            {
                "principal": self.vault.PRINCIPAL_CAPITAL_CENTS / 100,
                "currentProfit": (self.vault.current_balance - self.vault.start_of_day_balance)
                / 100,
                "lockThreshold": self.vault.DAILY_PROFIT_THRESHOLD_CENTS / 100,
                "isLocked": self.vault.is_locked,
                "total": self.vault.current_balance / 100,
            },
            self.name,
        )
