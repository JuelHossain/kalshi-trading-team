"""
Order Execution Logic for Hand Agent
Handles trade validation, order placement, and notifications.
"""

import os

import aiohttp
from agents.brain.simulation import kelly_fraction
from core import constants, trading_mode


def parse_orderbook(raw, side: str = "yes") -> dict | None:
    """Normalise a Kalshi orderbook into the requested side's own price space.

    Returns None when the book is unreadable. Otherwise:
        best_bid    best resting bid for `side`, in cents, or None if empty
        best_ask    best price to buy `side` at, in cents, or None if empty
        ask_levels  [(price_cents, contracts)] ascending -- what a buyer
                    of `side` crosses, for the depth check

    Kalshi quotes one book and no explicit asks: a resting NO bid at x IS a
    YES ask at 100 - x, and the reverse. Every shape is reduced to YES-side
    bid levels and NO-side bid levels first, then mirrored for the side
    requested.

    Three shapes are accepted:

      orderbook_fp   {"yes_dollars": [["0.3300","21717"], ...],
                      "no_dollars":  [["0.6500","77618"], ...]}
                     What the API returns today. Dollars as strings, sizes
                     as decimal strings. Levels ascending by price, so the
                     FIRST entry is the worst bid, not the best -- a 1c
                     junk bid sits at the front of nearly every book.
      orderbook      {"yes": [[33, 100], ...], "no": [[65, 50], ...]}
                     The previous API shape, integer cents.
      bids/asks      [{"price": 45, "count": 300}, ...]
                     Not a Kalshi shape. It is what the existing tests
                     construct; kept so they continue to exercise the
                     spread and depth logic below.

    The previous implementation read only the third shape. Against a real
    book both lookups missed and fell to their defaults of 45 and 55, so
    every snipe check reported a 10c spread and every approved signal died
    here. The engine never placed an order, paper or otherwise.
    """
    if not isinstance(raw, dict):
        return None

    def _levels(entries, *, dollars: bool):
        out = []
        for entry in entries or []:
            try:
                price, size = entry[0], entry[1]
                cents = round(float(price) * 100) if dollars else int(price)
                out.append((cents, float(size)))
            except (TypeError, ValueError, IndexError):
                continue
        return out

    yes_bids: list[tuple[int, float]] = []
    no_bids: list[tuple[int, float]] = []
    explicit_yes_asks: list[tuple[int, float]] | None = None

    fp = raw.get("orderbook_fp")
    legacy = raw.get("orderbook")
    if isinstance(fp, dict):
        yes_bids = _levels(fp.get("yes_dollars"), dollars=True)
        no_bids = _levels(fp.get("no_dollars"), dollars=True)
    elif isinstance(legacy, dict):
        yes_bids = _levels(legacy.get("yes"), dollars=False)
        no_bids = _levels(legacy.get("no"), dollars=False)
    elif "bids" in raw or "asks" in raw:
        yes_bids = [
            (int(lvl["price"]), float(lvl.get("count", 0)))
            for lvl in raw.get("bids", [])
            if isinstance(lvl, dict) and "price" in lvl
        ]
        explicit_yes_asks = [
            (int(lvl["price"]), float(lvl.get("count", 0)))
            for lvl in raw.get("asks", [])
            if isinstance(lvl, dict) and "price" in lvl
        ]
        # A YES ask at p is a NO bid at 100 - p.
        no_bids = [(100 - p, q) for p, q in explicit_yes_asks]
    else:
        return None

    if side.lower() == "no":
        bids = no_bids
        asks = [(100 - p, q) for p, q in yes_bids]
    else:
        bids = yes_bids
        asks = (
            explicit_yes_asks
            if explicit_yes_asks is not None
            else [(100 - p, q) for p, q in no_bids]
        )

    asks = sorted((lvl for lvl in asks if 0 < lvl[0] < 100), key=lambda lvl: lvl[0])
    bids = [lvl for lvl in bids if 0 < lvl[0] < 100]

    return {
        "best_bid": max(p for p, _ in bids) if bids else None,
        "best_ask": asks[0][0] if asks else None,
        "ask_levels": asks,
    }


async def snipe_check(
    kalshi_client,
    ticker: str,
    log_callback,
    max_stake_cents: int | None = None,
    side: str = "yes",
) -> dict:
    """Analyze order book for best entry with zero slippage.

    Kalshi quotes one book; the NO side is its mirror, so a NO ask at price x
    is a YES bid at (100 - x). Prices are mirrored rather than fetching a
    second book.
    """
    if max_stake_cents is None:
        max_stake_cents = constants.HAND_MAX_STAKE_CENTS
    if not kalshi_client:
        await log_callback("Kalshi client unavailable. Cannot perform snipe check.", level="ERROR")
        return {"valid": False, "reason": "Kalshi client unavailable"}

    try:
        orderbook = await kalshi_client.get_orderbook(ticker)

        book = parse_orderbook(orderbook, side=side)
        if book is None:
            return {"valid": False, "reason": "orderbook unreadable"}
        best_bid, best_ask = book["best_bid"], book["best_ask"]
        if best_bid is None or best_ask is None:
            return {"valid": False, "reason": "one side of the book is empty"}

        spread = best_ask - best_bid

        if spread > 5:  # More than 5¢ spread = potential slippage
            return {
                "valid": False,
                "reason": f"Spread too wide: {spread}¢",
                "entry_price": best_ask,
            }

        # Liquidity Depth Validation: contracts resting at the price we
        # would cross, in the requested side's own price space.
        target_stake = max_stake_cents
        available_volume_cents = 0
        for price, count in book["ask_levels"]:
            if price <= best_ask:
                available_volume_cents += price * count
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
    max_stake_cents: int | None = None,
    probability: float | None = None,
    price_cents: int | None = None,
    kelly_factor: float | None = None,
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
    if max_stake_cents is None:
        max_stake_cents = constants.HAND_MAX_STAKE_CENTS
    if kelly_factor is None:
        kelly_factor = constants.HAND_KELLY_FRACTION
    if ev <= 0 or probability is None or price_cents is None:
        return 0

    fraction = kelly_fraction(probability, price_cents / 100.0) * kelly_factor
    if fraction <= 0:
        return 0

    # Tradeable, not merely available: once the profit lock engages only
    # house money is sized. Then clamped so no stake can carry the balance
    # through the hard floor -- the floor used to be checked only against
    # the balance before the trade.
    bankroll = vault.get_tradeable_balance()
    return min(int(bankroll * fraction), max_stake_cents, vault.get_floor_headroom())


async def execute_order(
    kalshi_client,
    vault,
    ticker: str,
    price: int,
    stake: int,
    max_stake_cents: int | None = None,
    log_callback=None,
    side: str = "yes",
) -> dict:
    """Place limit order on Kalshi v2 with comprehensive pre-trade validation.

    `side` is "yes" or "no". `price` is the price of that side, so the
    validation below is unchanged: both sides quote 1-99c.
    """

    if max_stake_cents is None:
        max_stake_cents = constants.HAND_MAX_STAKE_CENTS

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
        return {
            "success": False,
            "error": f"Stake ${stake/100:.2f} exceeds max ${max_stake_cents/100:.2f}",
        }

    # 5. Check available balance (house money only once the profit lock is on)
    available_balance = vault.get_tradeable_balance()
    if available_balance < stake:
        return {
            "success": False,
            "error": f"Insufficient funds: available=${available_balance/100:.2f}, required=${stake/100:.2f}",
        }

    # 6. Check hard floor -- after the trade, not just before it
    if vault.current_balance < vault.HARD_FLOOR_CENTS:
        return {"success": False, "error": "Hard floor breach - emergency lockdown active"}
    if stake > vault.get_floor_headroom():
        return {
            "success": False,
            "error": f"Stake ${stake/100:.2f} would take the balance below the hard floor",
        }

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
    except Exception as e:
        # Order failed - release the reserved funds
        vault.release_reservation(stake)
        return {"success": False, "error": str(e)[:100]}

    result = result or {}
    order_id = (
        result.get("order_id")
        or (result.get("order") or {}).get("order_id")
        or result.get("client_order_id")
    )

    # Kalshi V2 says how much filled. Orders are immediate-or-cancel, so the
    # rest was cancelled: confirm only what filled and release the remainder.
    # A paper fill carries no fill_count and is always complete.
    filled = result.get("fill_count")
    if filled is not None:
        try:
            filled_contracts = int(float(filled))
        except (TypeError, ValueError):
            filled_contracts = contract_count
        if filled_contracts <= 0:
            vault.release_reservation(stake)
            return {"success": False, "error": "Order did not fill (immediate-or-cancel)"}
        filled_stake = min(stake, filled_contracts * price)
        vault.confirm_reservation(filled_stake)
        if stake > filled_stake:
            vault.release_reservation(stake - filled_stake)
        return {"success": True, "order_id": order_id, "stake": filled_stake}

    vault.confirm_reservation(stake)
    return {"success": True, "order_id": order_id, "stake": stake}


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
    # Paper fills never reach Kalshi's portfolio. Without this, a paper run
    # read an empty demo book, answered "not held", and doubled into two
    # markets in its first successful cycle. Checked first and unconditionally:
    # a paper holding is a holding.
    if trading_mode.paper_position(ticker) != 0:
        return True

    if not kalshi_client:
        return False

    try:
        positions = await kalshi_client.get_positions()
    except Exception:
        return True

    return any(
        (p.get("ticker") or p.get("market_id")) == ticker and p.get("position")
        for p in positions or []
    )
