"""
Queue Monitoring Logic for Brain Agent
Continuous monitoring and processing of opportunities from Synapse.
"""
import asyncio
from datetime import datetime

from core.flow_control import check_execution_queue_limit, should_restock


async def monitor_queue(
    brain_agent,
    stop_requested: bool,
    synapse,
    log_callback,
    process_callback
):
    """
    CONTINUOUS MONITORING LOOP
    Checks Synapse opportunity queue and processes ALL items until empty.

    Args:
        brain_agent: BrainAgent instance
        stop_requested: Flag to stop monitoring
        synapse: Synapse instance
        log_callback: Async function for logging
        process_callback: Async function to process single item
    """
    await log_callback("Starting continuous queue monitoring loop...", level="DEBUG")

    while not stop_requested:
        try:
            # Check if Synapse exists
            if not synapse:
                await asyncio.sleep(1)
                continue

            # FLOW CONTROL: Check if execution queue is at limit
            is_at_limit, exec_size = await check_execution_queue_limit(synapse)
            if is_at_limit:
                await log_callback(f"Flow Control: Execution queue at limit ({exec_size}/10). Pausing analysis.", level="WARN")
                await asyncio.sleep(2)
                continue

            # Check queue size
            queue_size = await synapse.opportunities.size()

            if queue_size == 0:
                # No opportunities - wait before checking again
                await asyncio.sleep(1)
                continue

            # Process ALL opportunities in queue until empty
            await log_callback(f"Found {queue_size} opportunities. Processing batch...", level="INFO")

            while queue_size > 0 and not stop_requested:
                # Check execution queue limit before each item
                is_at_limit, exec_size = await check_execution_queue_limit(synapse)
                if is_at_limit:
                    await log_callback(f"Flow Control: Execution queue at limit ({exec_size}/10). Stopping batch.", level="WARN")
                    break

                # Process ONE opportunity
                await process_callback()

                # Small delay between items
                await asyncio.sleep(0.5)

                # Update queue size
                queue_size = await synapse.opportunities.size()

            if queue_size == 0:
                await log_callback("Batch complete. All opportunities processed.", level="SUCCESS")
            else:
                await log_callback(f"Batch stopped. {queue_size} opportunities remaining.", level="DEBUG")

        except Exception as e:
            await log_callback(f"Monitor loop error: {str(e)[:100]}", level="ERROR")
            await asyncio.sleep(2)

    await log_callback("Monitoring loop stopped.", level="INFO")


async def process_single_item_from_queue(
    brain_agent,
    synapse,
    log_callback,
    process_opportunity_callback,
    bus,
    dumped_count: int,
    last_restock_time: float
) -> str:
    """
    Process ONE opportunity from Synapse queue.

    Args:
        brain_agent: BrainAgent instance
        synapse: Synapse instance
        log_callback: Async function for logging
        process_opportunity_callback: Async function to analyze opportunity
        bus: EventBus instance
        dumped_count: Current veto count
        last_restock_time: Last restock timestamp

    Returns:
        Result string ("APPROVED", "VETOED", "STALE", "SKIPPED")
    """
    # Pop one opportunity from queue
    opp_model = await synapse.opportunities.pop()
    if not opp_model:
        return "EMPTY"  # Queue was empty

    await log_callback(f"Synapse Input: {opp_model.ticker}")

    # Map Pydantic Model -> Legacy Dict for compatibility
    opp_dict = opp_model.model_dump()

    # Fix Price: Model has int (50), Brain logic expects float (0.50)
    kalshi_cents = opp_model.market_data.yes_price
    opp_dict["kalshi_price"] = kalshi_cents / 100.0

    # Ensure flattened structure matches expectations
    opp_dict["market_data"] = opp_model.market_data.model_dump()

    # Track decision
    result = await process_opportunity_callback(opp_dict)

    return result


async def handle_restock_trigger(
    result: str,
    dumped_count: int,
    last_restock_time: float,
    synapse,
    bus,
    log_callback
):
    """
    Handle restock triggering when opportunities are vetoed.

    Args:
        result: Processing result
        dumped_count: Current veto count
        last_restock_time: Last restock timestamp
        synapse: Synapse instance
        bus: EventBus instance
        log_callback: Async function for logging

    Returns:
        Tuple of (should_reset_counter, new_last_restock_time)
    """
    if result in ("VETOED", "STALE", "SKIPPED"):
        # When 5 opportunities dumped, request restock from Senses
        if dumped_count >= 5:
            import time
            now = time.time()

            # Check if we should restock using centralized flow control
            should_request = await should_restock(
                synapse,
                dumped_count,
                last_restock_time,
                now
            )

            exec_size = await synapse.executions.size() if synapse else 0

            if should_request:
                await log_callback(f"Dumped {dumped_count} opportunities. Requesting restock from Senses...")
                await bus.publish("REQUEST_RESTOCK", {}, "BRAIN")
                return (True, now)  # Reset counter and update time
            elif exec_size >= 10:
                await log_callback(f"Flow Control: Execution queue at limit ({exec_size}/10). NOT requesting restock.", level="WARN")
            else:
                cooldown = 60  # 60 seconds cooldown
                await log_callback(f"Flow Control: Restock cooldown active ({cooldown - (now - last_restock_time):.0f}s remaining).", level="DEBUG")

            return (True, last_restock_time)  # Reset counter only
    elif result == "APPROVED":
        return (True, last_restock_time)  # Reset dumped counter on approval

    return (False, last_restock_time)  # Don't reset


def check_opportunity_freshness(opportunity: dict, log_callback) -> tuple[bool, str]:
    """
    Check if opportunity is fresh (not stale).

    Args:
        opportunity: Market opportunity data
        log_callback: Async function for logging

    Returns:
        Tuple of (is_fresh, status_string)
    """
    ticker = opportunity.get("ticker", "UNKNOWN")

    # Reject opportunities older than 60 seconds
    now = datetime.now()
    ts = opportunity.get("timestamp")

    # Handle both datetime objects and ISO strings
    if isinstance(ts, str):
        try:
            ts = datetime.fromisoformat(ts)
        except ValueError:
            ts = None

    if ts:
        age = (now - ts).total_seconds()
        if age >= 60:  # Use >= to handle boundary case of exactly 60 seconds
            asyncio.create_task(log_callback(f"[STALE] Opportunity expired: {ticker} (Age: {age:.0f}s) - skipping", level="WARN"))
            return (False, "STALE")
    else:
        # For safety, if no timestamp exists, treat as potentially stale
        asyncio.create_task(log_callback(f"[STALE] Opportunity has no timestamp: {ticker} - skipping for safety", level="WARN"))
        return (False, "STALE")

    return (True, "FRESH")
