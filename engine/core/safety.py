"""Ragnarok: the emergency exit.

Cancel every resting order, then flatten every position at the extreme
tick. Getting out matters more than the last cent, so nothing here rests in
the book. Invoked by POST /ragnarok and by the Hand on a fatal error.
"""

import asyncio
from typing import Any

from core.display import AgentType, log_critical, log_error, log_info
from core.network import kalshi_client


async def execute_ragnarok() -> dict[str, Any]:
    """
    RAGNAROK PROTOCOL: emergency flattening.

    1. Cancel every resting order, so nothing new can fill mid-liquidation.
    2. Close every open position.
    3. Report both.

    Step 2 did not exist. The protocol cancelled unfilled orders and stopped,
    which meant it could not reduce exposure at all -- a filled order is a
    position, and nothing here could touch one. A test comment claimed this
    called kalshi_client.close_all_positions(); no such method existed.

    Cancelling first is deliberate: flattening while orders are still resting
    invites a fill against the exit.
    """
    log_critical("INITIATING RAGNAROK PROTOCOL...", AgentType.HAND)

    cancelled_count, orders_found = await _cancel_all_orders()
    positions_closed, positions_found = await _close_all_positions()

    log_critical(
        f"RAGNAROK COMPLETE. Cancelled {cancelled_count}/{orders_found} orders, "
        f"closed {positions_closed}/{positions_found} positions.",
        AgentType.HAND,
    )

    return {
        "status": "success",
        "orders_found": orders_found,
        "orders_cancelled": cancelled_count,
        "positions_found": positions_found,
        "positions_closed": positions_closed,
        "message": (
            f"Ragnarok complete. Cancelled {cancelled_count} orders, "
            f"closed {positions_closed} positions."
        ),
    }


async def _cancel_all_orders() -> tuple[int, int]:
    """Cancel every resting order. Returns (cancelled, found).

    Having no orders to cancel is not a reason to stop: the positions below
    still need closing, and in a real emergency the orders have usually already
    filled, which is exactly why there are positions.
    """
    try:
        response = await kalshi_client.request(
            "GET", "/portfolio/orders", params={"status": "active"}
        )
    except Exception as e:
        log_error(f"Ragnarok could not read orders: {e}", AgentType.HAND)
        return (0, 0)

    orders = (response or {}).get("orders") or []
    if not orders:
        log_info("No active orders to cancel.", AgentType.HAND)
        return (0, 0)

    log_critical(f"Found {len(orders)} active orders. CANCELLING ALL.", AgentType.HAND)

    async def cancel_one(order_id: str) -> bool:
        """Cancel a single resting order; True on success."""
        try:
            result = await kalshi_client.request("DELETE", f"/portfolio/orders/{order_id}")
        except Exception as e:
            log_error(f"Failed to cancel order {order_id}: {e}", AgentType.HAND)
            return False
        if result:
            log_info(f"Cancelled order {order_id}", AgentType.HAND)
            return True
        log_error(f"Failed to cancel order {order_id}", AgentType.HAND)
        return False

    tasks = [cancel_one(o["order_id"]) for o in orders if o.get("order_id")]
    results = await asyncio.gather(*tasks)
    return (sum(1 for r in results if r), len(orders))


async def _close_all_positions() -> tuple[int, int]:
    """Sell every open holding. Returns (closed, found).

    Never raises: this runs on the emergency path, and a failure to read
    positions must not prevent the order cancellations above from being
    reported.
    """
    try:
        positions = await kalshi_client.get_positions()
    except Exception as e:
        log_error(f"Ragnarok could not read positions: {e}", AgentType.HAND)
        return (0, 0)

    open_positions = [p for p in positions if p.get("position")]
    if not open_positions:
        log_info("No open positions to close.", AgentType.HAND)
        return (0, 0)

    log_critical(f"Closing {len(open_positions)} open positions.", AgentType.HAND)

    async def close_one(position: dict) -> bool:
        """Flatten a single position at the extreme tick; True on success."""
        ticker = position.get("ticker") or position.get("market_id")
        quantity = int(position.get("position", 0))
        count = abs(quantity)
        if not ticker or count <= 0:
            return False
        # Kalshi signs the quantity: negative means a NO holding (same rule
        # hand/agent.py's check_exits uses). Without this, every close went
        # through close_position's side="yes" default, so a NO holding was
        # never sold -- close_position built a "sell yes" order against a
        # position that had no YES to sell, instead of flattening the NO
        # actually held.
        side = "no" if quantity < 0 else "yes"
        try:
            result = await kalshi_client.close_position(ticker, count, side=side)
        except Exception as e:
            log_error(f"Failed to close {ticker}: {e}", AgentType.HAND)
            return False
        if result:
            log_info(f"Closed {count} contracts of {ticker}", AgentType.HAND)
            return True
        log_error(f"Failed to close {ticker}", AgentType.HAND)
        return False

    results = await asyncio.gather(*[close_one(p) for p in open_positions])
    return (sum(1 for r in results if r), len(open_positions))
