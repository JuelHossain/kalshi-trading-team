"""Ragnarok: the emergency exit.

Cancel every resting order, then flatten every position at the extreme
tick. Getting out matters more than the last cent, so nothing here rests in
the book. Invoked by POST /ragnarok.
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
    3. Report both, honestly.

    Which book it flattens follows the operator's durable choice,
    IS_PAPER_TRADING, not whether this process happens to have armed live
    placement. After a restart nothing is armed until a live cycle runs, and
    in that window Ragnarok used to cancel real orders (it calls Kalshi
    directly) while its closes became paper fills -- real positions left
    open, reported as "closed N/N".

    - Pinned to paper: flatten the paper book and leave Kalshi alone; report
      any real positions found as untouched.
    - Not pinned: cancel and close on Kalshi, arming live placement for the
      flatten whether or not a cycle has yet.

    Cancelling first is deliberate: flattening while orders are still resting
    invites a fill against the exit.
    """
    from core import trading_mode
    from core.settings import settings

    log_critical("INITIATING RAGNAROK PROTOCOL...", AgentType.HAND)

    if settings.get_bool("IS_PAPER_TRADING"):
        return await _paper_ragnarok()

    was_live = trading_mode.is_live()
    trading_mode.set_live(True)
    try:
        cancelled_count, orders_found = await _cancel_all_orders()
        positions_closed, positions_found = await _close_all_positions()
    finally:
        trading_mode.set_live(was_live)

    # found is -1 when positions could not be read: that is not "nothing to
    # close", it is "cannot say", and must not be reported as complete.
    complete = (
        positions_found >= 0
        and cancelled_count == orders_found
        and positions_closed == positions_found
    )
    log_critical(
        f"RAGNAROK {'COMPLETE' if complete else 'INCOMPLETE'}. Cancelled "
        f"{cancelled_count}/{orders_found} orders, closed "
        f"{positions_closed}/{positions_found} positions.",
        AgentType.HAND,
    )

    return {
        "status": "success" if complete else "partial",
        "mode": "live",
        "orders_found": orders_found,
        "orders_cancelled": cancelled_count,
        "positions_found": positions_found,
        "positions_closed": positions_closed,
        "message": (
            f"Ragnarok {'complete' if complete else 'INCOMPLETE'}. Cancelled "
            f"{cancelled_count}/{orders_found} orders, closed "
            f"{positions_closed}/{positions_found} positions."
        ),
    }


async def _paper_ragnarok() -> dict[str, Any]:
    """Flatten the paper book; never touch Kalshi. Report real exposure seen."""
    from core import trading_mode

    trading_mode.set_live(False)
    holdings = [p for p in trading_mode.paper_positions() if p.get("position")]
    closed = 0
    for position in holdings:
        quantity = int(position["position"])
        side = "no" if quantity < 0 else "yes"
        try:
            if await kalshi_client.close_position(position["ticker"], abs(quantity), side=side):
                closed += 1
        except Exception as e:
            log_error(f"Failed to close paper {position['ticker']}: {e}", AgentType.HAND)

    # Read-only: say plainly if there is real exposure this did not touch.
    real = 0
    try:
        real = len([p for p in (await kalshi_client.get_positions() or []) if p.get("position")])
    except Exception as e:
        log_error(f"Ragnarok could not read Kalshi positions: {e}", AgentType.HAND)

    message = f"Paper Ragnarok: closed {closed}/{len(holdings)} paper positions."
    if real:
        message += (
            f" {real} real Kalshi position(s) left untouched -- IS_PAPER_TRADING is pinned;"
            " unpin it on the host to flatten them."
        )
    log_critical(message, AgentType.HAND)
    return {
        "status": "success" if closed == len(holdings) else "partial",
        "mode": "paper",
        "orders_found": 0,
        "orders_cancelled": 0,
        "positions_found": len(holdings),
        "positions_closed": closed,
        "real_positions_untouched": real,
        "message": message,
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
        return (0, -1)

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
