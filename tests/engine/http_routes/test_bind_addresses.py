"""The engine must not listen on every interface by default.

It bound 0.0.0.0, and Fedora Workstation's default zone opens 1025-65535/tcp,
so the public control routes were reachable from the Wi-Fi LAN and Docker,
not only over Tailscale.
"""

import socket

import aiohttp
import pytest
from aiohttp import web
from http_api.server import start_server


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


async def _ok(_request):
    return web.json_response({"ok": True})


def _app():
    app = web.Application()
    app.router.add_get("/ping", _ok)
    return app


@pytest.mark.asyncio
@pytest.mark.network_internals
async def test_default_is_loopback_only(monkeypatch):
    monkeypatch.delenv("GHOST_BIND", raising=False)
    port = _free_port()

    runner = await start_server(_app(), port=port)

    hosts = {address[0] for address in runner.addresses}
    assert hosts == {"127.0.0.1"}, f"listening on {hosts}"
    async with aiohttp.ClientSession() as s, s.get(f"http://127.0.0.1:{port}/ping") as r:
        assert r.status == 200
    await runner.cleanup()


@pytest.mark.asyncio
@pytest.mark.network_internals
async def test_an_address_that_is_not_up_does_not_fail_the_start(monkeypatch):
    """tailscale0 can come up after the service; that must not be a crash."""
    monkeypatch.setenv("GHOST_BIND", "127.0.0.1,10.255.255.254")
    port = _free_port()

    runner = await start_server(_app(), port=port)  # must not raise

    async with aiohttp.ClientSession() as s, s.get(f"http://127.0.0.1:{port}/ping") as r:
        assert r.status == 200
    await runner.cleanup()
