"""
Market Scanning Logic for Senses Agent
Handles Kalshi market fetching, filtering, and stock management.
"""
import re
from datetime import UTC, datetime, timedelta

from core.error_dispatcher import ErrorSeverity
from core.flow_control import check_execution_queue_limit

# Compiled regex for ticker date parsing
TICKER_DATE_PATTERN = re.compile(r"(\d{2}[A-Z]{3}\d{2})")


# Kalshi lists enormous numbers of multi-variate "cross category" combo
# shards. They carry no volume, no quotes and machine-generated titles, and
# they dominate the market listing -- 8,000 consecutive markets during
# investigation were all shards. Excluded by prefix so they never consume a
# page of results.
MVE_PREFIX = "KXMVE"

MIN_VOLUME = 200
MAX_SPREAD_CENTS = 8
MAX_DAYS_TO_CLOSE = 10


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


def is_today_market(market: dict) -> bool:
    """Retained for compatibility; real selection is is_tradeable."""
    return is_tradeable(market)


async def fetch_kalshi_markets(kalshi_client, log_callback) -> list[dict]:
    """Fetch active markets from Kalshi (requests more for filtering)"""
    if not kalshi_client:
        await log_callback("ERROR: Kalshi client not initialized.", level="ERROR")
        return []

    try:
        # Bound by close time server-side, otherwise the response is all
        # combo shards and nothing tradeable is ever reached.
        now = datetime.now(UTC)
        markets = await kalshi_client.get_active_markets(
            limit=1000,
            min_close_ts=int(now.timestamp()),
            max_close_ts=int((now + timedelta(days=MAX_DAYS_TO_CLOSE)).timestamp()),
        )

        if markets is None:
            await log_callback(
                "ERROR: Kalshi API request failed - check network and credentials",
                level="ERROR",
            )
            return []

        if not isinstance(markets, list):
            await log_callback(
                f"ERROR: Expected list of markets, got {type(markets).__name__}",
                level="ERROR",
            )
            return []

        tradeable = [m for m in markets if is_tradeable(m)]
        tradeable.sort(key=lambda m: _money(m.get("volume_fp")), reverse=True)

        await log_callback(
            f"Filtered to {len(tradeable)} tradeable markets from {len(markets)} "
            f"fetched (volume >= {MIN_VOLUME}, spread <= {MAX_SPREAD_CENTS}c)",
            level="INFO",
        )

        return tradeable

    except Exception as e:
        await log_callback(f"Kalshi fetch error: {str(e)[:100]}", level="ERROR")
        return []


async def queue_from_stock(
    market_stock: list[dict],
    queue_batch_size: int,
    synapse,
    log_callback,
    fetch_context_callback,
    queue_opportunity_callback
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
        title = market.get("title", ticker)

        # Fetch context
        context_snippets = await fetch_context_callback(ticker, title)
        context_str = "\n".join(context_snippets)

        opportunity = {
            "ticker": ticker,
            "kalshi_price": kalshi_price,
            "vegas_prob": None,
            "volume": volume,
            "market_data": market,
            "source": "Volume-Algo",
            "external_context": context_str
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
        markets = await fetch_kalshi_markets(senses_agent.kalshi_client, log_callback)

        if not markets:
            await log_callback("No markets found to scan.", level="WARN")
            return

        await log_callback(f"Fetched {len(markets)} markets from Kalshi API")

        # 2. Sort by volume and take top markets
        sorted_markets = sorted(markets, key=lambda x: x.get("volume", 0), reverse=True)
        top_markets = sorted_markets[:stock_buffer_size]

        # 3. Populate stock buffer
        senses_agent.market_stock = top_markets
        await log_callback(f"Stock buffer populated with {len(senses_agent.market_stock)} markets")

        # 4. Queue top batch from stock
        queued = await queue_from_stock(
            market_stock=senses_agent.market_stock,
            queue_batch_size=queue_batch_size,
            synapse=senses_agent.synapse,
            log_callback=log_callback,
            fetch_context_callback=senses_agent.fetch_market_context,
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
