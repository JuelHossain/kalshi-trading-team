"""register_all_routes must wire each URL to the handler its name promises.

Every other safety test (test_kill_switch_atomicity.py,
test_halts_reach_the_hand.py, test_autopilot_routes.py) calls the handler
functions directly, so none of them would notice if register_all_routes
wired a URL to the wrong handler -- swapping the /kill-switch and
/deactivate-kill-switch registrations, or the /autopilot/start and
/autopilot/stop ones, inside register_all_routes still left the rest of the
suite green. These tests build the real aiohttp app from register_all_routes
and POST to the paths the cockpit actually uses (useEngineFeed.ts's
ENGINE_URL is "/api"), so a swap like that fails here.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
from core import trading_mode
from http_api.routes import register_all_routes


@pytest.fixture
def engine():
    return SimpleNamespace(
        bus=SimpleNamespace(publish=AsyncMock()),
        vault=MagicMock(),
        synapse=None,
        soul=None,
        manual_kill_switch=False,
        is_processing=False,
        cycle_count=0,
        last_cycle_time=None,
    )


async def _client(engine):
    app = web.Application()
    register_all_routes(app, engine)
    client = TestClient(TestServer(app))
    await client.start_server()
    return client


@pytest.mark.asyncio
@pytest.mark.parametrize("prefix", ["", "/api"])
async def test_kill_switch_sets_the_halt(engine, prefix):
    client = await _client(engine)
    try:
        resp = await client.post(f"{prefix}/kill-switch")
        assert resp.status == 200
        assert engine.manual_kill_switch is True
        assert trading_mode.is_halted()
    finally:
        await client.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("prefix", ["", "/api"])
async def test_deactivate_kill_switch_lifts_the_halt(engine, prefix):
    client = await _client(engine)
    try:
        await client.post(f"{prefix}/kill-switch")

        resp = await client.post(f"{prefix}/deactivate-kill-switch")

        assert resp.status == 200
        assert engine.manual_kill_switch is False
        assert not trading_mode.is_halted()
    finally:
        await client.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("prefix", ["", "/api"])
async def test_cancel_stops_autopilot_and_releases_reservations(engine, prefix):
    client = await _client(engine)
    try:
        resp = await client.post(f"{prefix}/cancel")

        assert resp.status == 200
        published = [call.args[:2] for call in engine.bus.publish.await_args_list]
        assert ("SYSTEM_CONTROL", {"action": "STOP_AUTOPILOT"}) in published
        engine.vault.release_all_reservations.assert_called_once()
    finally:
        await client.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("prefix", ["", "/api"])
async def test_autopilot_start_publishes_exactly_start_autopilot(engine, prefix):
    client = await _client(engine)
    try:
        resp = await client.post(f"{prefix}/autopilot/start", json={})

        assert resp.status == 200
        engine.bus.publish.assert_awaited_once_with(
            "SYSTEM_CONTROL", {"action": "START_AUTOPILOT", "isPaperTrading": True}, "HTTP"
        )
    finally:
        await client.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("prefix", ["", "/api"])
async def test_autopilot_stop_publishes_exactly_stop_autopilot(engine, prefix):
    client = await _client(engine)
    try:
        resp = await client.post(f"{prefix}/autopilot/stop")

        assert resp.status == 200
        engine.bus.publish.assert_awaited_once_with(
            "SYSTEM_CONTROL", {"action": "STOP_AUTOPILOT"}, "HTTP"
        )
    finally:
        await client.close()
