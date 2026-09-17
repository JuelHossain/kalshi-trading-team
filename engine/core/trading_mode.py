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

# What paper mode holds. Kalshi's portfolio never sees a simulated fill, so
# anything that asks "do we already hold this?" by reading Kalshi gets an
# empty book back in paper mode and answers "no". The first successful paper
# run doubled into two markets that way. Keyed by ticker; "position" is
# signed the way Kalshi signs it: YES contracts positive, NO negative.
_paper_positions: dict[str, dict] = {}


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
    _record_paper_fill(ticker, side, price, count, action)
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


def _record_paper_fill(ticker: str, side: str, price: int, count: int, action: str) -> None:
    """Apply a simulated fill to the paper book.

    A buy adds signed contracts and the cents paid. A sell removes them and
    releases exposure in proportion, since Kalshi reports exposure rather
    than an average price and the exit policy derives entry from the ratio.
    """
    signed = int(count) if side.lower() == "yes" else -int(count)
    row = _paper_positions.get(ticker, {"ticker": ticker, "position": 0, "market_exposure": 0})

    if action.lower() == "sell":
        held = row["position"]
        if held:
            per_contract = abs(row["market_exposure"]) / abs(held)
            row["market_exposure"] = max(
                0, round(abs(row["market_exposure"]) - per_contract * abs(count))
            )
        row["position"] = held - signed
    else:
        row["position"] = row["position"] + signed
        row["market_exposure"] = abs(row["market_exposure"]) + int(price) * int(count)

    if row["position"] == 0:
        _paper_positions.pop(ticker, None)
    else:
        _paper_positions[ticker] = row


def paper_position(ticker: str) -> int:
    """Signed contracts held on paper for `ticker`; 0 if none."""
    return int(_paper_positions.get(ticker, {}).get("position", 0))


def paper_positions() -> list[dict]:
    """Every paper holding, shaped like a Kalshi market_positions row.

    Carries "position" and "market_exposure", which is what
    average_entry_price_cents and the exit review read.
    """
    return [dict(row) for row in _paper_positions.values()]


def reset_paper_positions() -> None:
    """Forget every paper holding. For tests and for a deliberate reset."""
    _paper_positions.clear()
