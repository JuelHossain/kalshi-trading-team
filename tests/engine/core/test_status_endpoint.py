"""/api/status must report what the engine will actually do.

The dashboard could not answer its most important question -- is this about to
spend real money, and where? -- because nothing reported it. ModeIndicator
derived "Live Trading" from an auth-session flag, and SystemHealth reported
Kalshi "Authenticated (RSA-SHA256)" whenever a key-id string existed in the
browser's config, having never contacted Kalshi.

The danger in a status endpoint is the same one: reporting a value that is
merely supposed to agree with behaviour rather than the value governing it. So
these tests change the real switches and require the endpoint to follow.
"""
import pytest
from aiohttp import web

from core import trading_mode
from http_api.routes import get_engine_status


class _Vault:
    kill_switch_active = False
    HARD_FLOOR_CENTS = 25500
    current_balance = 30000
    principal_locked = False


class _Engine:
    vault = _Vault()
    manual_kill_switch = False
    running = True
    is_processing = False
    cycle_count = 7
    agents = []
    last_cycle_time = None


@pytest.fixture(autouse=True)
def _restore_mode():
    before = trading_mode.is_live()
    yield
    trading_mode.set_live(before)


async def _status(engine=None) -> dict:
    """Call the handler directly; a real request object adds nothing here."""
    handler = get_engine_status(engine or _Engine())
    response: web.Response = await handler(object())
    import json

    return json.loads(response.text)


@pytest.mark.asyncio
async def test_orders_are_real_follows_the_actual_switch():
    """The field must read the switch place_order consults, not a copy of it.

    A status endpoint reporting a separate flag would let the UI say PAPER while
    the engine sends live orders -- exactly the defect this replaces.
    """
    trading_mode.set_live(False)
    assert (await _status())["orders_are_real"] is False

    trading_mode.set_live(True)
    assert (await _status())["orders_are_real"] is True


@pytest.mark.asyncio
async def test_venue_reports_demo_by_default(monkeypatch):
    monkeypatch.delenv("KALSHI_ENV", raising=False)

    venue = (await _status())["venue"]

    assert venue["env"] == "demo"
    assert venue["base_url"] == "https://demo-api.kalshi.co/trade-api/v2"
    assert venue["is_production"] is False


@pytest.mark.asyncio
async def test_venue_reports_production_when_selected(monkeypatch):
    monkeypatch.setenv("KALSHI_ENV", "prod")

    venue = (await _status())["venue"]

    assert venue["is_production"] is True
    assert venue["base_url"] == "https://api.kalshi.co/trade-api/v2"
    assert venue["credential_vars"] == ["KALSHI_PROD_KEY_ID", "KALSHI_PROD_PRIVATE_KEY"]


@pytest.mark.asyncio
async def test_credentials_present_requires_both_halves(monkeypatch):
    """A key id without a private key cannot authenticate, so it is not 'present'."""
    monkeypatch.setenv("KALSHI_ENV", "demo")
    monkeypatch.setenv("KALSHI_DEMO_KEY_ID", "id")
    monkeypatch.delenv("KALSHI_DEMO_PRIVATE_KEY", raising=False)

    assert (await _status())["venue"]["credentials_present"] is False


@pytest.mark.asyncio
async def test_never_returns_a_credential(monkeypatch):
    """Status is served to a browser. It must describe secrets, never carry them."""
    monkeypatch.setenv("KALSHI_ENV", "demo")
    monkeypatch.setenv("KALSHI_DEMO_KEY_ID", "super-secret-key-id")
    monkeypatch.setenv("KALSHI_DEMO_PRIVATE_KEY", "super-secret-private-key")

    handler = get_engine_status(_Engine())
    body: web.Response = await handler(object())

    assert "super-secret-key-id" not in body.text
    assert "super-secret-private-key" not in body.text


@pytest.mark.asyncio
async def test_halted_reflects_the_vault_not_a_copy():
    engine = _Engine()
    engine.vault = _Vault()
    engine.vault.kill_switch_active = True
    engine.vault.current_balance = 100

    halted = (await _status(engine))["halted"]

    assert halted["kill_switch"] is True
    assert halted["below_hard_floor"] is True


@pytest.mark.asyncio
async def test_headroom_is_the_distance_to_the_floor():
    engine = _Engine()
    engine.vault = _Vault()
    engine.vault.current_balance = 28000

    vault = (await _status(engine))["vault"]

    assert vault["headroom_cents"] == 28000 - 25500


@pytest.mark.asyncio
async def test_paper_pin_is_reported(monkeypatch):
    monkeypatch.setenv("IS_PAPER_TRADING", "true")
    assert (await _status())["paper_pinned_by_env"] is True

    monkeypatch.setenv("IS_PAPER_TRADING", "false")
    assert (await _status())["paper_pinned_by_env"] is False
