"""
Safety & Risk Management Core
"""
import asyncio
from typing import Any

from core.display import AgentType, log_info, log_warning, log_error, log_critical
from core.network import kalshi_client


async def execute_ragnarok() -> dict[str, Any]:
    """
    RAGNAROK PROTOCOL: Emergency liquidation of all open orders.
    1. Fetch all open orders.
    2. Cancel each one asynchronously.
    3. Return usage report.
    """
    log_critical("INITIATING RAGNAROK PROTOCOL...", AgentType.HAND)

    # 1. Fetch Open Orders
    # Kalshi API V2: GET /portfolio/orders?status=active
    path = "/portfolio/orders"
    params = {"status": "active"}

    response = await kalshi_client.request("GET", path, params=params)

    if not response or "orders" not in response:
        log_warning("No active orders found or API failed.", AgentType.HAND)
        return {"status": "success", "orders_cancelled": 0, "message": "No active orders found."}

    orders = response["orders"]
    if not orders:
        log_info("No active orders to cancel.", AgentType.HAND)
        return {"status": "success", "orders_cancelled": 0, "message": "No active orders."}

    log_critical(f"Found {len(orders)} active orders. CANCELLING ALL.", AgentType.HAND)

    # 2. Cancel All Orders
    cancelled_count = 0
    tasks = []

    async def cancel_order(order_id: str):
        # DELETE /portfolio/orders/{order_id}
        c_path = f"/portfolio/orders/{order_id}"
        c_res = await kalshi_client.request("DELETE", c_path)
        if c_res:
            log_info(f"Cancelled order {order_id}", AgentType.HAND)
            return True
        log_error(f"Failed to cancel order {order_id}", AgentType.HAND)
        return False

    for order in orders:
        order_id = order.get("order_id")
        if order_id:
            tasks.append(cancel_order(order_id))

    results = await asyncio.gather(*tasks)
    cancelled_count = sum(1 for r in results if r)

    log_critical(f"RAGNAROK COMPLETE. Cancelled {cancelled_count}/{len(orders)} orders.", AgentType.HAND)

    return {
        "status": "success",
        "orders_found": len(orders),
        "orders_cancelled": cancelled_count,
        "message": f"Ragnarok complete. Cancelled {cancelled_count} orders."
    }
