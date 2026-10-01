"""Ragnarok: the emergency exit.

Cancel every resting order, then flatten every position at the extreme
tick. Getting out matters more than the last cent, so nothing here rests in
the book. Invoked by POST /ragnarok.
"""

import asyncio
from typing import Any

from core.display import AgentType, log_critical, log_error, log_info
from core.ledger import record_exit
from core.network import kalshi_client


async def _closing_bid_cents(ticker: str, side: str) -> int | None:
    """Best resting bid on `side`, read just after the close order fills.

    Ragnarok's own close is a 1c marketable limit (KalshiClient.close_position)
    so it guarantees a fill, not a price the ledger can use -- the same reason
    hand/agent.py's check_exits prices its own exits from the book rather than
    from the close order. Unlike check_exits, which reads its exit price
    *before* placing the close, both callers here call this only after
    close_position has already returned: the 1c marketable sell has already
    hit the book by the time this reads it, so it is the best approximation
    available afterwards, not literally what the close itself traded at.
    agents.hand.execution is the one place that knows the orderbook's shapes
    (see its own docstring); imported here, not at module scope, to keep
    core from depending on agents at import time.

    Never raises: a failed read must not stop the position from having been
    flattened, it just leaves the ledger row's exit price unknown.
    """
    from agents.hand.execution import parse_orderbook

    try:
        raw = await kalshi_client.get_orderbook(ticker)
    except Exception as e:
        log_error(f"Could not price the {ticker} exit for the ledger: {e}", AgentType.HAND)
        return None
    book = parse_orderbook(raw, side=side)
    return book["best_bid"] if book else None


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
    - Not pinned: cancel and close on Kalshi. The closes pass live=True to
      close_position explicitly (see _close_all_positions) instead of
      toggling the process-wide trading_mode._live flag for the whole
      flatten -- that used to arm every other coroutine's buys for the
      duration too (a paper-approved signal reaching place_order mid-flatten
      would go out as a real order), and a concurrent cycle's
      set_live(False) could just as easily disarm Ragnarok's own closes back
      to paper fills. The caller (routes.trigger_ragnarok) halts new
      exposure before calling this, so the only thing that can happen to a
      concurrent buy is refusal, not a real fill.

    Cancelling first is deliberate: flattening while orders are still resting
    invites a fill against the exit.
    """
    from core.settings import settings

    log_critical("INITIATING RAGNAROK PROTOCOL...", AgentType.HAND)

    if settings.get_bool("IS_PAPER_TRADING"):
        return await _paper_ragnarok()

    cancelled_count, orders_found = await _cancel_all_orders()
    positions_closed, positions_found = await _close_all_positions()

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
        ticker = position["ticker"]
        quantity = int(position["position"])
        side = "no" if quantity < 0 else "yes"
        try:
            result = await kalshi_client.close_position(ticker, abs(quantity), side=side)
        except Exception as e:
            log_error(f"Failed to close paper {ticker}: {e}", AgentType.HAND)
            continue
        if result:
            closed += 1
            # Outside the try above: the close itself already succeeded, so
            # a failure reading the book afterwards must not be reported as
            # "Failed to close paper" -- _closing_bid_cents never raises and
            # leaves the exit price unknown instead. Without this call, an
            # exited fill sits unsettled and later gets priced off however
            # the market resolves (see core.ledger.record_exit).
            record_exit(ticker, side, await _closing_bid_cents(ticker, side))

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
            # live=True: this close must reach Kalshi regardless of what the
            # process-wide trading_mode flag says at this instant -- a
            # concurrent paper cycle's set_live(False) (main.py, before
            # authorize_cycle) must not turn an emergency close into a
            # paper fill that leaves the real position open behind a
            # "closed N/N" report.
            result = await kalshi_client.close_position(ticker, count, side=side, live=True)
        except Exception as e:
            log_error(f"Failed to close {ticker}: {e}", AgentType.HAND)
            return False
        if result:
            log_info(f"Closed {count} contracts of {ticker}", AgentType.HAND)
            # Without this, an exited fill sits unsettled and later gets
            # priced off however the market resolves (see
            # core.ledger.record_exit), not off what this flatten actually
            # fetched.
            record_exit(ticker, side, await _closing_bid_cents(ticker, side))
            return True
        log_error(f"Failed to close {ticker}", AgentType.HAND)
        return False

    results = await asyncio.gather(*[close_one(p) for p in open_positions])
    return (sum(1 for r in results if r), len(open_positions))
