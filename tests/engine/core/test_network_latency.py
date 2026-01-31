import pytest
import time
from engine.core.network import kalshi_client

@pytest.mark.asyncio
async def test_network_ping_latency():
    """Verify market data fetch latency stays within reasonable bounds."""
    start_time = time.time()
    
    # Fetch a known stable ticker or just the balance
    await kalshi_client.get_balance()
    
    latency = (time.time() - start_time) * 1000 # ms
    print(f"\n[NETWORK] Ping Latency: {latency:.2f}ms")
    
    # Threshold for concern (adjust as needed)
    assert latency < 2000, "Network latency too high (>2s)"
