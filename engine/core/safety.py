"""
Safety & Risk Management Core
"""
import asyncio
from typing import Dict, List, Any
from colorama import Fore, Style
from core.network import kalshi_client

async def execute_ragnarok() -> Dict[str, Any]:
    """
    RAGNAROK PROTOCOL: Emergency liquidation of all open orders.
    1. Fetch all open orders.
    2. Cancel each one asynchronously.
    3. Return usage report.
    """
    print(f"{Fore.RED}[SAFETY] ⚠️ INITIATING RAGNAROK PROTOCOL...{Style.RESET_ALL}")
    
    # 1. Fetch Open Orders
    # Kalshi API V2: GET /portfolio/orders?status=active
    path = "/portfolio/orders"
    params = {"status": "active"}
    
    response = await kalshi_client.request("GET", path, params=params)
    
    if not response or "orders" not in response:
        print(f"{Fore.YELLOW}[SAFETY] No active orders found or API failed.{Style.RESET_ALL}")
        return {"status": "success", "orders_cancelled": 0, "message": "No active orders found."}
    
    orders = response["orders"]
    if not orders:
        print(f"{Fore.GREEN}[SAFETY] No active orders to cancel.{Style.RESET_ALL}")
        return {"status": "success", "orders_cancelled": 0, "message": "No active orders."}
    
    print(f"{Fore.RED}[SAFETY] Found {len(orders)} active orders. CANCELLING ALL.{Style.RESET_ALL}")
    
    # 2. Cancel All Orders
    cancelled_count = 0
    tasks = []
    
    async def cancel_order(order_id: str):
        # DELETE /portfolio/orders/{order_id}
        c_path = f"/portfolio/orders/{order_id}"
        c_res = await kalshi_client.request("DELETE", c_path)
        if c_res:
            print(f"{Fore.GREEN}[SAFETY] Cancelled order {order_id}{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.RED}[SAFETY] Failed to cancel order {order_id}{Style.RESET_ALL}")
            return False

    for order in orders:
        order_id = order.get("order_id")
        if order_id:
            tasks.append(cancel_order(order_id))
            
    results = await asyncio.gather(*tasks)
    cancelled_count = sum(1 for r in results if r)
    
    print(f"{Fore.RED}[SAFETY] RAGNAROK COMPLETE. Cancelled {cancelled_count}/{len(orders)} orders.{Style.RESET_ALL}")
    
    return {
        "status": "success", 
        "orders_found": len(orders),
        "orders_cancelled": cancelled_count,
        "message": f"Ragnarok complete. Cancelled {cancelled_count} orders."
    }
