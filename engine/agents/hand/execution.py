"""
Order Execution Logic for Hand Agent
Handles trade validation, order placement, and notifications.
"""
import os

import aiohttp
from core.constants import HAND_MAX_STAKE_CENTS, HAND_PROFIT_LOCK_THRESHOLD


async def snipe_check(kalshi_client, ticker: str, log_callback, max_stake_cents: int = HAND_MAX_STAKE_CENTS) -> dict:
    """Analyze order book for best entry with zero slippage"""
    if not kalshi_client:
        await log_callback("Kalshi client unavailable. Cannot perform snipe check.", level="ERROR")
        return {"valid": False, "reason": "Kalshi client unavailable"}

    try:
        orderbook = await kalshi_client.get_orderbook(ticker)

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

        # Liquidity Depth Validation
        target_stake = max_stake_cents
        available_volume_cents = 0

        # Aggregate volume within the actual spread
        for ask in orderbook.get("asks", []):
            price = ask.get("price", 100)
            count = ask.get("count", 0)

            if price <= best_ask:
                available_volume_cents += (price * count)
            else:
                break

        if available_volume_cents < (target_stake * 2):
            return {
                "valid": False,
                "reason": "insufficient liquidity depth",
                "entry_price": best_ask,
            }

        return {"valid": True, "entry_price": best_ask, "slippage": 0, "spread": spread}
    except Exception as e:
        return {"valid": False, "reason": str(e)[:50]}


def calculate_kelly_stake(confidence: float, ev: float, vault, max_stake_cents: int = HAND_MAX_STAKE_CENTS) -> int:
    """Kelly Criterion with conservative factor"""
    if ev <= 0:
        return 0

    # Simplified Kelly with 25% fraction (quarter Kelly for safety)
    kelly_fraction = max(0, (confidence - 0.5) * 0.5) * 0.25

    # Calculate stake in cents
    available = min(vault.current_balance, max_stake_cents)
    stake = int(available * kelly_fraction)

    # Cap at max stake
    return min(stake, max_stake_cents)


async def execute_order(
    kalshi_client,
    vault,
    ticker: str,
    price: int,
    stake: int,
    max_stake_cents: int = HAND_MAX_STAKE_CENTS,
    log_callback=None
) -> dict:
    """Place limit order on Kalshi v2 with comprehensive pre-trade validation."""

    # === PRE-TRADE VALIDATION ===

    # 1. Check kill switch
    if vault.kill_switch_active:
        return {"success": False, "error": "Kill switch active - trading halted"}

    # 2. Validate ticker format
    if not ticker or not isinstance(ticker, str) or len(ticker) < 3:
        return {"success": False, "error": f"Invalid ticker format: {ticker}"}

    # 3. Validate price range (Kalshi: 1-99 cents)
    if not isinstance(price, int) or price < 1 or price > 99:
        return {"success": False, "error": f"Price must be 1-99 cents, got: {price}"}

    # 4. Validate stake
    if not isinstance(stake, int) or stake <= 0:
        return {"success": False, "error": f"Stake must be positive integer, got: {stake}"}

    if stake > max_stake_cents:
        return {"success": False, "error": f"Stake ${stake/100:.2f} exceeds max ${max_stake_cents/100:.2f}"}

    # 5. Check available balance
    available_balance = vault.get_available_balance()
    if available_balance < stake:
        return {
            "success": False,
            "error": f"Insufficient funds: available=${available_balance/100:.2f}, required=${stake/100:.2f}"
        }

    # 6. Check hard floor
    if vault.current_balance < vault.HARD_FLOOR_CENTS:
        return {"success": False, "error": "Hard floor breach - emergency lockdown active"}

    # === LIVE TRADING ===
    if not kalshi_client:
        return {"success": False, "error": "Kalshi client unavailable - cannot execute trade"}
    # Calculate contract count
    contract_count = stake // price
    if contract_count <= 0:
        return {"success": False, "error": f"Stake ${stake/100:.2f} too small for price {price}¢"}

    # Reserve funds atomically before placing order
    if not vault.reserve_funds(stake):
        return {"success": False, "error": "Failed to reserve funds"}

    try:
        result = await kalshi_client.place_order(
            ticker=ticker,
            side="yes",
            type="limit",
            price=price,
            count=contract_count,
        )

        # Order placed successfully - confirm the reservation
        vault.confirm_reservation(stake)
        return {"success": True, "order_id": result.get("order_id")}

    except Exception as e:
        # Order failed - release the reserved funds
        vault.release_reservation(stake)
        return {"success": False, "error": str(e)[:100]}


async def send_notification(ticker: str, stake: int, result: dict, log_callback=None):
    """Send push notification via ntfy.sh"""
    ntfy_topic = os.environ.get("NTFY_TOPIC", "kalshi-alerts")
    if not ntfy_topic:
        return

    try:
        async with aiohttp.ClientSession() as session:
            message = f"Trade Executed: {ticker}\nStake: ${stake/100:.2f}\nOrder: {result.get('order_id', 'N/A')}"
            await session.post(
                f"https://ntfy.sh/{ntfy_topic}",
                data=message.encode(),
                headers={
                    "Title": "Kalshi Trade Alert",
                    "Priority": "high",
                    "Tags": "money_with_wings",
                },
            )
            if log_callback:
                await log_callback("Push notification sent.")
    except Exception as e:
        if log_callback:
            await log_callback(f"Notification failed: {str(e)[:30]}", level="ERROR")
