import asyncio
import os
import sys

import pytest
import pytest_asyncio
from dotenv import load_dotenv

# Ensure we are loading the engine environment
engine_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../engine"))
sys.path.append(engine_path)
load_dotenv(os.path.join(engine_path, ".env"))

# ---------------------------------------------------------------------------
# Credentials
# ---------------------------------------------------------------------------
# Unit tests must never require real secrets. Several constructors only check
# that a credential is *present*, so a placeholder lets them run -- previously
# these tests failed rather than skipped, and CI could never be green.
#
# Record whether genuine credentials were supplied BEFORE filling placeholders
# in. Tests that actually reach the Kalshi API are marked `live` and skipped
# unless real credentials exist, so placeholders never cause a real network
# call that would hang or fail confusingly.

HAS_LIVE_CREDENTIALS = bool(
    os.getenv("KALSHI_PROD_KEY_ID") and os.getenv("KALSHI_PROD_PRIVATE_KEY")
)

_PLACEHOLDER_VARS: set[str] = set()

for _var, _placeholder in {
    "GHOST_API_KEY": "test-ghost-api-key",
    # Both environments are seeded because KalshiClient reads the pair matching
    # KALSHI_ENV, which defaults to demo. Seeding only one pair would make the
    # suite pass or fail on which environment happened to be selected.
    "KALSHI_DEMO_KEY_ID": "test-kalshi-key-id",
    "KALSHI_DEMO_PRIVATE_KEY": "test-kalshi-private-key",
    "KALSHI_PROD_KEY_ID": "test-kalshi-key-id",
    "KALSHI_PROD_PRIVATE_KEY": "test-kalshi-private-key",
    "AUTH_PASSWORD": "test-auth-password",
}.items():
    if os.getenv(_var):
        continue
    os.environ[_var] = _placeholder
    _PLACEHOLDER_VARS.add(_var)


def has_real_credentials(*names: str) -> bool:
    """Whether these variables came from the environment rather than from us.

    Presence is not enough: the placeholders above are set for every run, so a
    test that skipped on `not os.getenv(...)` would stop skipping the moment a
    placeholder was added for that name and would then try to reach the real
    Kalshi API with a fake key.
    """
    return all(os.getenv(n) and n not in _PLACEHOLDER_VARS for n in names)


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "live: hits the real Kalshi API; skipped without real credentials"
    )


def pytest_collection_modifyitems(config, items):
    if HAS_LIVE_CREDENTIALS:
        return
    skip_live = pytest.mark.skip(
        reason="needs real credentials (KALSHI_PROD_KEY_ID, KALSHI_PROD_PRIVATE_KEY)"
    )
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip_live)


from unittest.mock import AsyncMock

from agents.brain import BrainAgent
from agents.hand import HandAgent
from core.bus import EventBus
from core.network import kalshi_client
from core.synapse import Synapse
from core.vault import RecursiveVault


@pytest.fixture(autouse=True)
def block_network(request, monkeypatch):
    """Fail fast instead of dialling out.

    Placeholder credentials let KalshiClient construct, so an unmocked call
    would attempt a real HTTP request and stall ~2s per test on a timeout.
    Every HTTP method funnels through request(), so blocking that single method
    covers every module that imported the client, however it was bound.

    Tests marked `live` opt out and use the real client. Tests marked
    `network_internals` opt out because they exercise request() itself
    against a fake session -- the retry and error-classification logic
    cannot be tested through a blocked request().
    """
    if "live" in request.keywords or "network_internals" in request.keywords:
        return

    from core.network import KalshiClient

    async def _blocked(*_args, **_kwargs):
        raise RuntimeError(
            "Network is disabled in tests. Mock the Kalshi client, "
            "or mark the test with @pytest.mark.live."
        )

    monkeypatch.setattr(KalshiClient, "request", _blocked)


@pytest.fixture(autouse=True)
def isolate_databases(tmp_path, monkeypatch):
    """Point every test at throwaway databases.

    Vault and Synapse otherwise write to the real engine/ghost_memory.db and
    ghost_memory.db. Vault.initialize() reloads persisted reservations from
    there, so one test's reserved funds leaked into the next and some tests
    passed or failed purely on run order.

    Autouse so no test can opt out by forgetting a fixture.
    """
    monkeypatch.setenv("GHOST_VAULT_DB", str(tmp_path / "vault.db"))
    monkeypatch.setenv("GHOST_SYNAPSE_DB", str(tmp_path / "synapse.db"))
    monkeypatch.setenv("GHOST_LEDGER_DB", str(tmp_path / "ledger.db"))
    monkeypatch.setenv("GHOST_JOURNAL_DB", str(tmp_path / "journal.db"))


@pytest.fixture(scope="session")
def event_loop():
    """Create a session-scoped event loop."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_db(tmp_path):
    """A fresh SQLite path for one test.

    This used to be a fixed filename in the working directory, deleted at
    setup and teardown. Two problems: a queue from the previous test could
    still hold the file open, so the delete at setup raised on Windows and
    took the next test down with it; and interrupted runs left dozens of
    test_ghost_memory_*.db files behind. A per-test tmp_path has neither.
    """
    return str(tmp_path / "test_ghost_memory.db")


@pytest_asyncio.fixture(scope="function")
async def bus():
    return EventBus()


@pytest_asyncio.fixture(scope="function")
async def synapse(test_db):
    return Synapse(db_path=test_db)


@pytest_asyncio.fixture(scope="function")
async def vault(test_db):
    """Create a vault in test mode (no persistence)."""
    v = RecursiveVault(test_mode=True)  # Enable test mode
    # Initialize with a safe test amount (in cents)
    await v.initialize(100000)  # $1000
    yield v


@pytest_asyncio.fixture(scope="function")
async def k_client():
    """Real Kalshi client authenticated with Demo credentials from .env."""
    # Ensure we ARE in paper trading mode for safety
    os.environ["IS_PRODUCTION"] = "false"

    # Check if we have credentials
    if not has_real_credentials("KALSHI_DEMO_KEY_ID", "KALSHI_DEMO_PRIVATE_KEY"):
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


# Shared by the trade-cycle, exit-policy, no-side and duplicate-exposure tests.
# Lived in test_trade_cycle.py and was imported from there; pytest finds it
# here without any module having to import a fixture by name.
@pytest.fixture
def cycle(test_db):
    """A Brain and Hand wired to one bus, one synapse and a funded vault."""
    bus = EventBus()
    synapse = Synapse(db_path=test_db)
    vault = RecursiveVault(test_mode=True)

    kalshi = AsyncMock()
    kalshi.get_balance = AsyncMock(return_value=100_000)  # $1000
    kalshi.get_orderbook = AsyncMock(
        return_value={
            "bids": [{"price": 48, "count": 400}],
            "asks": [{"price": 51, "count": 400}],
        }
    )
    kalshi.place_order = AsyncMock(return_value={"order_id": "integration-order-1"})

    brain = BrainAgent(3, bus, synapse=synapse)
    hand = HandAgent(4, bus, vault=vault, kalshi_client=kalshi, synapse=synapse)
    return {
        "bus": bus,
        "synapse": synapse,
        "vault": vault,
        "kalshi": kalshi,
        "brain": brain,
        "hand": hand,
    }
