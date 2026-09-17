"""
Market Scanning Logic for Senses Agent
Handles Kalshi market fetching, filtering, and stock management.
"""
from datetime import UTC, datetime, timedelta

from core.error_dispatcher import ErrorSeverity
from core.flow_control import check_execution_queue_limit

# Kalshi lists enormous numbers of multi-variate "cross category" combo
# shards. They carry no volume, no quotes and machine-generated titles, and
# they dominate the market listing -- 8,000 consecutive markets during
# investigation were all shards. Excluded by prefix so they never consume a
# page of results.
MVE_PREFIX = "KXMVE"

MIN_VOLUME = 200
MAX_SPREAD_CENTS = 8
MAX_DAYS_TO_CLOSE = 10

# Markets requested per page, and the ceiling on pages walked before giving
# up. Paging exists only because combo shards crowd out real markets; the
# loop stops the moment the stock buffer is full, so a normal restock reads
# far fewer than the ceiling.
MARKET_PAGE_SIZE = 500
MAX_MARKET_PAGES = 8


def _money(value) -> float:
    """Kalshi returns prices and volumes as decimal strings, not numbers."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def market_probability(market: dict) -> float | None:
    """The market's implied probability of YES, or None if unquoted.

    Prices arrive as *_dollars strings, so they are already 0-1. The old
    code read a "yes_price" key that no longer exists, so every market
    silently defaulted to 0.50 and the Brain scored a phantom price.
    """
    bid = _money(market.get("yes_bid_dollars"))
    ask = _money(market.get("yes_ask_dollars"))
    if 0 < bid < 1 and 0 < ask < 1:
        return (bid + ask) / 2
    last = _money(market.get("last_price_dollars"))
    return last if 0 < last < 1 else None


def is_tradeable(market: dict) -> bool:
    """Reject markets whose price carries no information.

    A zero-volume market with no quotes has no opinion to disagree with, so
    analysing it burns an AI call to compare an estimate against nothing.
    """
    if str(market.get("ticker", "")).startswith(MVE_PREFIX):
        return False

    bid = _money(market.get("yes_bid_dollars"))
    ask = _money(market.get("yes_ask_dollars"))
    if not (0 < bid < 1 and 0 < ask < 1):
        return False
    # Compare in whole cents. Kalshi quotes in cents, and doing this in
    # floats rejects the exact boundary: (0.33 - 0.25) * 100 evaluates to
    # 8.000000000000002, so an 8c spread failed an "at most 8c" rule.
    if round(ask * 100) - round(bid * 100) > MAX_SPREAD_CENTS:
        return False

    return _money(market.get("volume_fp")) >= MIN_VOLUME


async def fetch_kalshi_markets(
    kalshi_client, log_callback, needed: int = 30, exclude=frozenset()
) -> list[dict]:
    """Return up to `needed` tradeable markets, best volume first.

    `exclude` is a set of tickers to skip -- typically those queued recently.
    Restock re-fetched the top of the same volume ranking every time, so the
    same ten NFL markets were analysed cycle after cycle: a grounded Gemini
    call each, and the same approval reaching the Hand again. Paging continues
    past excluded tickers until `needed` new ones are found.

    Walks pages only until the stock buffer can be filled. The buffer is
    then drained a batch at a time across cycles, so one restock covers
    several cycles and no cycle pulls thousands of markets it will discard.
    """
    if not kalshi_client:
        await log_callback("ERROR: Kalshi client not initialized.", level="ERROR")
        return []

    now = datetime.now(UTC)
    min_close = int(now.timestamp())
    max_close = int((now + timedelta(days=MAX_DAYS_TO_CLOSE)).timestamp())

    tradeable: list[dict] = []
    seen = 0
    cursor: str | None = None

    try:
        for _ in range(MAX_MARKET_PAGES):
            page, cursor = await kalshi_client.get_markets_page(
                limit=MARKET_PAGE_SIZE,
                min_close_ts=min_close,
                max_close_ts=max_close,
                cursor=cursor,
            )
            if not page:
                break

            seen += len(page)
            tradeable.extend(
                m for m in page
                if is_tradeable(m) and m.get("ticker") not in exclude
            )

            if len(tradeable) >= needed or not cursor:
                break

        tradeable.sort(key=lambda m: _money(m.get("volume_fp")), reverse=True)
        selected = tradeable[:needed]

        await log_callback(
            f"Selected {len(selected)} tradeable markets from {seen} scanned "
            f"(volume >= {MIN_VOLUME}, spread <= {MAX_SPREAD_CENTS}c, "
            f"closing within {MAX_DAYS_TO_CLOSE}d)",
            level="INFO",
        )
        return selected

    except Exception as e:
        await log_callback(f"Kalshi fetch error: {str(e)[:100]}", level="ERROR")
        return []


async def queue_from_stock(
    market_stock: list[dict],
    queue_batch_size: int,
    synapse,
    log_callback,
    queue_opportunity_callback,
) -> int:
    """Queue top markets from stock buffer to Synapse"""
    if not market_stock:
        await log_callback("Stock buffer empty. Cannot queue.", level="WARN")
        return 0

    # Take top QUEUE_BATCH_SIZE from stock
    to_queue = market_stock[:queue_batch_size]
    remaining = market_stock[queue_batch_size:]

    await log_callback(f"Queueing {len(to_queue)} markets from stock (remaining in stock: {len(remaining)})")

    queued_count = 0
    for market in to_queue:
        # Convert market dict to opportunity format
        ticker = market.get("ticker", "")
        kalshi_price = market_probability(market)
        if kalshi_price is None:
            await log_callback(f"Skipping unquoted market {ticker}", level="WARN")
            continue
        volume = int(_money(market.get("volume_fp")))
        opportunity = {
            "ticker": ticker,
            "kalshi_price": kalshi_price,
            "vegas_prob": None,
            "volume": volume,
            "market_data": market,
            "source": "Volume-Algo",
        }

        await queue_opportunity_callback(opportunity)
        queued_count += 1

    await log_callback(f"Queued {queued_count} markets from stock to Synapse")

    # Verify queue size
    if synapse:
        queue_size = await synapse.opportunities.size()
        await log_callback(f"Synapse Queue Size: {queue_size}", level="INFO")

    return queued_count


async def surveillance_loop(
    senses_agent,
    stock_buffer_size: int,
    queue_batch_size: int,
    log_callback,
    log_error_callback,
    bus
):
    """Main scanning loop - pure Python, no AI tokens"""
    try:
        # FLOW CONTROL: Check if execution queue is at limit
        if senses_agent.synapse:
            is_at_limit, exec_size = await check_execution_queue_limit(senses_agent.synapse)
            if is_at_limit:
                await log_callback(f"Flow Control: Execution queue at limit ({exec_size}/10). Pausing surveillance.", level="WARN")
                return

        # 1. Fetch Kalshi markets
        markets = await fetch_kalshi_markets(
            senses_agent.kalshi_client, log_callback, needed=stock_buffer_size,
            exclude=senses_agent.recently_queued(),
        )

        if not markets:
            await log_callback("No markets found to scan.", level="WARN")
            return

        await log_callback(f"Fetched {len(markets)} markets from Kalshi API")

        # fetch_kalshi_markets already filtered, sorted by volume and truncated.
        senses_agent.market_stock = markets
        await log_callback(f"Stock buffer populated with {len(senses_agent.market_stock)} markets")

        # 4. Queue top batch from stock
        await queue_from_stock(
            market_stock=senses_agent.market_stock,
            queue_batch_size=queue_batch_size,
            synapse=senses_agent.synapse,
            log_callback=log_callback,
            queue_opportunity_callback=senses_agent.queue_opportunity
        )

        # 5. Signal Brain that opportunities are ready
        queue_size = await senses_agent.synapse.opportunities.size() if senses_agent.synapse else 0
        await bus.publish(
            "OPPORTUNITIES_READY",
            {
                "count": queue_size,
                "source": "SENSES",
            },
            senses_agent.name,
        )
        await log_callback("Signaled Brain: OPPORTUNITIES_READY event published")

    except Exception as e:
        await log_callback(f"Surveillance error: {str(e)[:100]}", level="ERROR")
        await log_error_callback(
            code="NETWORK_CONNECTION_FAILED",
            message=f"Senses Surveillance Failed: {e!s}",
            severity=ErrorSeverity.CRITICAL,
            exception=e
        )
        await bus.publish("SYSTEM_FATAL", {"message": f"Senses Agent Failed: {e!s}"}, senses_agent.name)
