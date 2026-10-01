"""A page on another site must not be able to drive the engine through the browser.

A cross-site POST with a "simple" body (text/plain, a form) needs no CORS
preflight, and aiohttp's request.json() parses it whatever the Content-Type.
The audit reproduced one such request turning off paper trading and zeroing
the hard floor through /config, and the public control routes (/autopilot/start,
/trigger, /reset) are reachable the same way. A browser always sends Origin on
such a POST and cannot send application/json cross-site without a preflight
the CORS allow-list refuses, so browser writes must be JSON. Non-browser
clients (curl, the systemd hook) send no Origin and are unaffected.
"""

import pytest
from aiohttp import web
from aiohttp.test_utils import make_mocked_request
from core.auth import auth_manager


async def _ok(_request):
    return web.json_response({"reached": True})


async def _call(method, path, headers):
    handler = await auth_manager.middleware(None, _ok)
    return await handler(make_mocked_request(method, path, headers=headers))


@pytest.mark.asyncio
@pytest.mark.parametrize("content_type", ["text/plain", "application/x-www-form-urlencoded", ""])
async def test_a_cross_site_simple_post_is_refused(content_type):
    headers = {"Origin": "http://evil.example"}
    if content_type:
        headers["Content-Type"] = content_type

    response = await _call("POST", "/api/autopilot/start", headers)

    assert response.status == 403


@pytest.mark.asyncio
async def test_the_cockpits_json_post_goes_through():
    headers = {"Origin": "http://j-bot-mini:3002", "Content-Type": "application/json"}

    response = await _call("POST", "/api/autopilot/start", headers)

    assert response.status == 200


@pytest.mark.asyncio
async def test_curl_without_an_origin_is_not_a_browser():
    response = await _call("POST", "/api/reset", {})

    assert response.status == 200


@pytest.mark.asyncio
async def test_reads_are_untouched():
    response = await _call("GET", "/api/health", {"Origin": "http://evil.example"})

    assert response.status == 200
