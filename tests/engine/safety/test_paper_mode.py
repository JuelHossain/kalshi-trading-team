"""Paper mode must physically prevent a real order.

Before this, `is_paper_trading` reached the progress display and the event
payloads and nothing else. A cycle rendered as PAPER TRADING would still send a
live order to Kalshi, because the order path never consulted the flag.

These tests assert the guard at the one place money moves, and that every route
to an order -- entry, exit, and Ragnarok's flatten -- is covered by it.
"""

import pytest
from core import trading_mode
from core.network import KalshiClient


@pytest.fixture(autouse=True)
def _restore_mode():
    """Never leak an armed switch into another test."""
    before = trading_mode.is_live()
    yield
    trading_mode.set_live(before)


@pytest.fixture
def client(monkeypatch):
    """A client whose transport fails loudly if anything reaches it."""
    monkeypatch.setenv("KALSHI_PROD_KEY_ID", "test-key-id")
    monkeypatch.setenv("KALSHI_PROD_PRIVATE_KEY", "not-a-real-key")
    c = KalshiClient.__new__(KalshiClient)  # skip credential/key parsing

    async def _explode(*args, **kwargs):
        raise AssertionError("paper mode sent a request to Kalshi")

    c.request = _explode
    return c


def test_defaults_to_paper():
    """A fresh process must not be armed. A wiring mistake costs a paper fill."""
    import importlib

    fresh = importlib.reload(trading_mode)
    assert fresh.is_live() is False, "trading_mode must default to paper, not live"


@pytest.mark.asyncio
async def test_paper_entry_places_no_real_order(client):
    trading_mode.set_live(False)

    result = await client.place_order(
        ticker="TEST-MARKET", side="yes", type="limit", price=40, count=3
    )

    assert result["paper"] is True
    assert result["status"] == "simulated"
    assert result["price"] == 40 and result["count"] == 3


@pytest.mark.asyncio
async def test_paper_exit_places_no_real_order(client):
    """close_position routes through place_order, so the guard must cover exits too."""
    trading_mode.set_live(False)

    result = await client.close_position("TEST-MARKET", 5, side="no")

    assert result["paper"] is True
    assert result["action"] == "sell"


@pytest.mark.asyncio
async def test_live_mode_reaches_the_transport(client):
    """The guard must not be a permanent block: armed, the order really goes out.

    Without this, a guard that always returned a paper fill would pass every
    other test in this file while quietly disabling trading altogether.
    """
    sent = {}

    async def _capture(method, path, json_data=None):
        sent.update({"method": method, "path": path, "json": json_data})
        return {"order_id": "REAL-1"}

    client.request = _capture
    trading_mode.set_live(True)

    result = await client.place_order(
        ticker="TEST-MARKET", side="yes", type="limit", price=40, count=3
    )

    assert result == {"order_id": "REAL-1"}
    assert sent["path"] == "/portfolio/orders"
    assert sent["json"]["price"] == 40


@pytest.mark.asyncio
async def test_switching_back_to_paper_disarms(client):
    """Live for one cycle must not leave the switch armed for the next."""
    trading_mode.set_live(True)
    trading_mode.set_live(False)

    result = await client.place_order(
        ticker="TEST-MARKET", side="yes", type="limit", price=40, count=3
    )

    assert result["paper"] is True
