import os
import sys
import pytest
import asyncio
import sqlite3
import pytest_asyncio
from dotenv import load_dotenv

# Ensure we are loading the engine environment
engine_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../engine"))
sys.path.append(engine_path)
load_dotenv(os.path.join(engine_path, ".env"))

from engine.core.bus import EventBus
from engine.core.synapse import Synapse
from engine.core.network import kalshi_client
from engine.core.vault import RecursiveVault

@pytest.fixture(scope="session")
def event_loop():
    """Create a session-scoped event loop."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="function")
async def test_db():
    """Create a temporary SQLite database for testing isolation."""
    db_path = "test_ghost_memory.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    
    yield db_path
    
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except PermissionError:
            pass # DB might still be locking on some systems

@pytest_asyncio.fixture(scope="function")
async def bus():
    return EventBus()

@pytest_asyncio.fixture(scope="function")
async def synapse(test_db):
    return Synapse(db_path=test_db)

@pytest_asyncio.fixture(scope="function")
async def vault():
    v = RecursiveVault()
    # Initialize with a safe test amount (in cents)
    await v.initialize(100000) # $1000
    return v

@pytest_asyncio.fixture(scope="function")
async def k_client():
    """Real Kalshi client authenticated with Demo credentials from .env."""
    # Ensure we ARE in paper trading mode for safety
    os.environ["IS_PRODUCTION"] = "false"
    
    # Check if we have credentials
    if not os.getenv("KALSHI_DEMO_KEY_ID") or not os.getenv("KALSHI_DEMO_PRIVATE_KEY"):
        pytest.skip("Kalshi Demo credentials not found in engine/.env")
        
    # Re-initialize to ensure it picks up the latest env (if needed)
    # kalshi_client is a singleton, so we just use the existing one
    # but we should ensure it's logged in.
    try:
        await kalshi_client.get_balance()
    except Exception as e:
        pytest.fail(f"Failed to authenticate with Kalshi Demo: {e}")
        
    yield kalshi_client
    # We don't close the client here as it might be used by other tests 
    # and it's a singleton in the engine.
