"""Whether orders are real.

`is_paper_trading` existed before this module, but only ever reached the
progress display and the event payloads. Nothing on the path that places an
order read it, so a cycle rendered in yellow as PAPER TRADING would still send
a live order to Kalshi. The label was cosmetic exactly where it mattered.

The switch lives here rather than being threaded through Soul -> Brain -> Hand
because the Hand is several events downstream of the request that chose the
mode, and every layer in between would have to carry a flag it does not
otherwise use. One switch, consulted at the single point where money moves
(`KalshiClient.place_order`, which entries, exits and Ragnarok all funnel
through), cannot be bypassed by a new call site that forgets to pass it along.

It is default-deny: until something explicitly enables live trading, orders are
simulated. A wiring mistake therefore costs a paper fill, not money.
"""

_live = False


def set_live(live: bool) -> None:
    """Arm or disarm real order placement. Returns nothing; call it once per cycle."""
    global _live
    _live = bool(live)


def is_live() -> bool:
    """Whether orders placed right now reach Kalshi."""
    return _live


def paper_fill(ticker: str, side: str, price: int, count: int, action: str) -> dict:
    """The response a simulated order returns.

    Shaped like a real fill so everything downstream -- reservation
    confirmation, notifications, the ledger, the dashboard -- runs the same code
    in paper as in live. A paper soak that skipped those paths would not be
    testing the thing that later handles real money.
    """
    return {
        "order_id": f"PAPER-{action.lower()}-{side.lower()}-{ticker}-{price}x{count}",
        "status": "simulated",
        "paper": True,
        "ticker": ticker,
        "side": side.lower(),
        "action": action.lower(),
        "price": price,
        "count": count,
    }
