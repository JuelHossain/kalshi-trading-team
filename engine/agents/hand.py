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

import asyncio
import aiohttp
import os
from datetime import datetime
from typing import Dict, Any, Optional
from agents.base import BaseAgent
from core.bus import EventBus
from core.vault import RecursiveVault
from core.db import log_to_db


class HandAgent(BaseAgent):
    """The Tactical Executioner - Precision Strike & Budget Sentinel"""
    
    MAX_STAKE_CENTS = 7500  # $75 max per trade
    PROFIT_LOCK_THRESHOLD = 5000  # $50 profit triggers principal lock
    NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "kalshi-alerts")
    
    def __init__(self, agent_id: int, bus: EventBus, vault: RecursiveVault, brain_agent=None, kalshi_client=None):
        super().__init__("HAND", agent_id, bus)
        self.vault = vault
        self.brain = brain_agent
        self.kalshi_client = kalshi_client
        self.pending_orders = []

    async def setup(self):
        await self.log("Hand online. Precision strike capability ready.")
        await self.bus.subscribe("EXECUTION_READY", self.on_execution_ready)

    async def on_execution_ready(self, message):
        """Execute approved trade from Brain"""
        await self.log("Execution signal received. Initiating strike sequence...")
        
        if not self.brain:
            await self.log("Brain agent not connected. Cannot execute.", level="ERROR")
            return
        
        target = self.brain.pop_execution_target()
        if not target:
            await self.log("No execution target available.")
            return
        
        ticker = target.get('ticker', 'UNKNOWN')
        confidence = target.get('confidence', 0)
        ev = target.get('ev', 0)
        
        await self.log(f"Target acquired: {ticker}")
        
        # 1. Snipe Check (Order Book Analysis)
        snipe_result = await self.snipe_check(ticker)
        if not snipe_result.get('valid'):
            await self.log(f"Snipe check failed: {snipe_result.get('reason')}", level="ERROR")
            return
        
        entry_price = snipe_result.get('entry_price', 50)
        
        # 2. Kelly Sizing
        stake = self.calculate_kelly_stake(confidence, ev)
        await self.log(f"Kelly sizing: ${stake/100:.2f} (Confidence: {confidence*100:.1f}%)")
        
        # 3. Execute Order
        order_result = await self.execute_order(ticker, entry_price, stake)
        
        if order_result.get('success'):
            await self.log(f"✅ ORDER EXECUTED: {ticker} @ {entry_price}¢ for ${stake/100:.2f}")
            
            # 4. Check for Vault Lock
            current_profit = self.vault.current_balance - self.vault.start_of_day_balance
            if current_profit >= self.PROFIT_LOCK_THRESHOLD and not self.vault.is_locked:
                self.vault.lock_principal()
                await self.log("🔒 VAULT LOCKED: $300 principal secured. Trading house money!")
            
            # 5. Send Notification
            await self.send_notification(ticker, stake, order_result)
            
            # Publish trade result for Soul to learn
            await self.bus.publish("TRADE_RESULT", {
                "outcome": "pending",  # Will update on settlement
                "ticker": ticker,
                "stake": stake,
                "entry_price": entry_price,
                "details": f"{ticker} at {entry_price}¢"
            }, self.name)
        else:
            await self.log(f"❌ ORDER FAILED: {order_result.get('error')}", level="ERROR")

    async def snipe_check(self, ticker: str) -> Dict:
        """Analyze order book for best entry with zero slippage"""
        if not self.kalshi_client:
            await self.log("Kalshi client unavailable. Simulating snipe check.")
            return {"valid": True, "entry_price": 50, "slippage": 0}
        
        try:
            orderbook = await self.kalshi_client.get_orderbook(ticker)
            
            # Find best bid/ask spread
            best_bid = orderbook.get('bids', [{}])[0].get('price', 45)
            best_ask = orderbook.get('asks', [{}])[0].get('price', 55)
            spread = best_ask - best_bid
            
            if spread > 5:  # More than 5¢ spread = potential slippage
                return {
                    "valid": False,
                    "reason": f"Spread too wide: {spread}¢",
                    "entry_price": best_ask
                }
            
            return {
                "valid": True,
                "entry_price": best_ask,
                "slippage": 0,
                "spread": spread
            }
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

    async def execute_order(self, ticker: str, price: int, stake: int) -> Dict:
        """Place limit order on Kalshi v2"""
        if not self.kalshi_client:
            await self.log("Kalshi client unavailable. Simulating order.")
            # Deduct from vault in simulation
            self.vault.current_balance -= stake
            return {"success": True, "order_id": "SIM-001", "simulated": True}
        
        if price <= 0 or stake <= 0:
            return {"success": False, "error": "Invalid price or stake"}

        try:
            result = await self.kalshi_client.place_order(
                ticker=ticker,
                side="yes",
                type="limit",
                price=price,
                count=stake // price  # Number of contracts
            )
            return {"success": True, "order_id": result.get('order_id')}
        except Exception as e:
            return {"success": False, "error": str(e)[:100]}

    async def send_notification(self, ticker: str, stake: int, result: Dict):
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
                        "Tags": "money_with_wings"
                    }
                )
                await self.log("Push notification sent.")
        except Exception as e:
            await self.log(f"Notification failed: {str(e)[:30]}", level="ERROR")

    async def run_execution(self, exec_queue: asyncio.Queue):
        """Execute trades from execution queue."""
        while True:
            try:
                # Get next execution
                execution = await exec_queue.get()
                await self.log(f"Executing: {execution['signal_id']} | Size: ${execution['suggested_size']}")

                # Placeholder: extract ticker from signal_id or add ticker to execution
                ticker = execution.get('ticker', 'PLACEHOLDER')  # Need to fix in brain
                price = 50  # Placeholder, should get from orderbook
                stake = execution['suggested_size']

                result = await self.execute_order(ticker, price, stake)

                if result.get('success'):
                    await log_to_db("trade_log", {
                        "signal_id": execution['signal_id'],
                        "ticker": ticker,
                        "stake": stake,
                        "result": result
                    })
                    await self.send_notification(ticker, stake, result)
                    await self.log(f"Trade executed: {ticker} | Stake: ${stake}")
                else:
                    await self.log(f"Trade failed: {result.get('error')}", level="ERROR")

            except Exception as e:
                await self.log(f"Execution error: {str(e)[:100]}", level="ERROR")
                await asyncio.sleep(1)

            await asyncio.sleep(1)

    async def on_tick(self, payload: Dict[str, Any]):
        pass  # Hand is event-driven

    async def on_tick(self, payload: Dict[str, Any]):
        """Periodic vault state broadcast"""
        # Emit vault update for UI
        await self.bus.publish("VAULT_UPDATE", {
            "principal": self.vault.PRINCIPAL_CAPITAL_CENTS / 100,
            "currentProfit": (self.vault.current_balance - self.vault.start_of_day_balance) / 100,
            "lockThreshold": self.vault.DAILY_PROFIT_THRESHOLD_CENTS / 100,
            "isLocked": self.vault.is_locked,
            "total": self.vault.current_balance / 100
        }, self.name)
