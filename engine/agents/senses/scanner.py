"""
Market Scanning Logic for Senses Agent
Handles Kalshi market fetching, filtering, and stock management.
"""
import re

from core.error_dispatcher import ErrorSeverity
from core.flow_control import check_execution_queue_limit

# Compiled regex for ticker date parsing
TICKER_DATE_PATTERN = re.compile(r"(\d{2}[A-Z]{3}\d{2})")


def is_today_market(market: dict) -> bool:
    """Check if market expires today (based on title or expiration time)"""
    title = market.get("title", "").lower()
    ticker = market.get("ticker", "")

    # Check ticker for today's date (e.g., 26JAN30 in KX...-26JAN30-...)
    if TICKER_DATE_PATTERN.search(ticker):
        return True

    return True  # Default to true if we can't determine


async def fetch_kalshi_markets(kalshi_client, log_callback) -> list[dict]:
    """Fetch active markets from Kalshi (requests more for filtering)"""
    if not kalshi_client:
        await log_callback("ERROR: Kalshi client not initialized.", level="ERROR")
        return []

    try:
        # Request more markets to have better selection (limit=100)
        markets = await kalshi_client.get_active_markets(limit=100)

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

        # Filter to today's markets only
        today_markets = [m for m in markets if is_today_market(m)]

        await log_callback(f"Filtered to {len(today_markets)} today's markets from {len(markets)} total", level="INFO")

        return today_markets

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
        kalshi_price = market.get("yes_price", 50) / 100
        volume = market.get("volume", 0)
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
