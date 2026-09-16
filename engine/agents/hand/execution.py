"""
Order Execution Logic for Hand Agent
Handles trade validation, order placement, and notifications.
"""
import os

import aiohttp
from core.constants import (
    HAND_KELLY_FRACTION,
    HAND_MAX_STAKE_CENTS,
    HAND_PROFIT_LOCK_THRESHOLD,
)
from agents.brain.simulation import kelly_fraction


async def snipe_check(
    kalshi_client,
    ticker: str,
    log_callback,
    max_stake_cents: int = HAND_MAX_STAKE_CENTS,
    side: str = "yes",
) -> dict:
    """Analyze order book for best entry with zero slippage.

    Kalshi quotes one book; the NO side is its mirror, so a NO ask at price x
    is a YES bid at (100 - x). Prices are mirrored rather than fetching a
    second book.
    """
    if not kalshi_client:
        await log_callback("Kalshi client unavailable. Cannot perform snipe check.", level="ERROR")
        return {"valid": False, "reason": "Kalshi client unavailable"}

    try:
        orderbook = await kalshi_client.get_orderbook(ticker)

        # Find best bid/ask spread
        raw_bid = orderbook.get("bids", [{}])[0].get("price", 45)
        raw_ask = orderbook.get("asks", [{}])[0].get("price", 55)

        if side.lower() == "no":
            # Buying NO means crossing the YES bid, mirrored: 100 - bid.
            best_bid, best_ask = 100 - raw_ask, 100 - raw_bid
        else:
            best_bid, best_ask = raw_bid, raw_ask

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
        depth_levels = orderbook.get("bids" if side.lower() == "no" else "asks", [])
        for level in depth_levels:
            raw_price = level.get("price", 100)
            price = 100 - raw_price if side.lower() == "no" else raw_price
            count = level.get("count", 0)

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


def calculate_kelly_stake(
    confidence: float,
    ev: float,
    vault,
    max_stake_cents: int = HAND_MAX_STAKE_CENTS,
    probability: float | None = None,
    price_cents: int | None = None,
    kelly_factor: float = HAND_KELLY_FRACTION,
) -> int:
    """Stake a fraction of Kelly, sized on the edge.

    Kelly for a binary contract costing k and paying 1 is (p - k)/(1 - k).

    The previous implementation did not use the edge at all. It sized on
    `(confidence - 0.5) * 0.5 * 0.25` -- the model's self-reported certainty --
    so a 1% edge and a 45% edge with equal confidence received an identical
    stake. It also multiplied that fraction by `min(balance, max_stake)` rather
    than by the bankroll, which capped the result at about 6% of the maximum:
    the $75 ceiling was unreachable, the real one being roughly $4.68.

    Confidence is now a gate rather than a sizing input, which is what it is
    good for: the Brain already refuses to trade below its threshold.

    Returns 0 rather than guessing when the probability or price is missing,
    so a wiring mistake cannot silently produce a mis-sized live order.
    """
    if ev <= 0 or probability is None or price_cents is None:
        return 0

    fraction = kelly_fraction(probability, price_cents / 100.0) * kelly_factor
    if fraction <= 0:
        return 0

    bankroll = vault.get_available_balance()
    return min(int(bankroll * fraction), max_stake_cents)


async def execute_order(
    kalshi_client,
    vault,
    ticker: str,
    price: int,
    stake: int,
    max_stake_cents: int = HAND_MAX_STAKE_CENTS,
    log_callback=None,
    side: str = "yes",
) -> dict:
    """Place limit order on Kalshi v2 with comprehensive pre-trade validation.

    `side` is "yes" or "no". `price` is the price of that side, so the
    validation below is unchanged: both sides quote 1-99c.
    """

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
            side=side.lower(),
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


async def has_open_position(kalshi_client, ticker: str) -> bool:
    """Whether the engine already holds this market.

    Nothing previously stopped the same ticker being scanned, approved and
    bought on cycle after cycle. Combined with having no exit path, exposure
    accumulated in a position the engine could neither see nor close.

    Fails closed: if positions cannot be read, the answer is "assume we hold
    it" and the trade is skipped. Declining a good trade costs an opportunity;
    doubling blindly into one costs money.
    """
    if not kalshi_client:
        return False

    try:
        positions = await kalshi_client.get_positions()
    except Exception:  # noqa: BLE001 - unreadable positions must not open new risk
        return True

    return any(
        (p.get("ticker") or p.get("market_id")) == ticker and p.get("position")
        for p in positions or []
    )
