import pytest
import os
from engine.core.network import kalshi_client

@pytest.mark.asyncio
async def test_kalshi_auth_demo():
    """Verify that we can authenticate with Kalshi Demo using credentials in .env."""
    # Ensure IS_PRODUCTION is false
    os.environ["IS_PRODUCTION"] = "false"
    
    # Check credentials existence
    assert os.getenv("KALSHI_DEMO_KEY_ID") is not None
    assert os.getenv("KALSHI_DEMO_PRIVATE_KEY") is not None
    
    # Try fetching balance as a proxy for successful auth
    try:
        balance = await kalshi_client.get_balance()
        assert isinstance(balance, int)
        print(f"\n[AUTH] Success! Balance: {balance/100:.2f}")
    except Exception as e:
        pytest.fail(f"Authentication failed: {e}")
