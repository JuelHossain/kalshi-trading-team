"""POST /autopilot/start and /autopilot/stop must actually reach the bus.

Both handlers are one line each -- publish a SYSTEM_CONTROL action and
return a JSON status -- and nothing exercised them: a no-op replacement for
either still left the full suite green. Soul's own reaction to
START_AUTOPILOT/STOP_AUTOPILOT is covered elsewhere (test_soul_lifecycle.py),
but the route-to-bus step itself was not.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from http_api.routes import start_autopilot, stop_autopilot


@pytest.fixture
def engine():
    return SimpleNamespace(bus=SimpleNamespace(publish=AsyncMock()))


def _request(body=None):
    req = SimpleNamespace()
    req.json = AsyncMock(return_value=body or {})
    return req


class TestStartAutopilot:
    @pytest.mark.asyncio
    async def test_publishes_start_autopilot(self, engine):
        response = await start_autopilot(engine)(_request({"isPaperTrading": True}))

        engine.bus.publish.assert_awaited_once_with(
            "SYSTEM_CONTROL", {"action": "START_AUTOPILOT", "isPaperTrading": True}, "HTTP"
        )
        assert response.status == 200

    @pytest.mark.asyncio
    async def test_honours_an_explicit_live_flag(self, engine):
        await start_autopilot(engine)(_request({"isPaperTrading": False}))

        engine.bus.publish.assert_awaited_once_with(
            "SYSTEM_CONTROL", {"action": "START_AUTOPILOT", "isPaperTrading": False}, "HTTP"
        )

    @pytest.mark.asyncio
    async def test_defaults_to_paper_when_the_field_is_missing(self, engine):
        """An empty body must not accidentally arm live autopilot."""
        await start_autopilot(engine)(_request({}))

        engine.bus.publish.assert_awaited_once_with(
            "SYSTEM_CONTROL", {"action": "START_AUTOPILOT", "isPaperTrading": True}, "HTTP"
        )


class TestStopAutopilot:
    @pytest.mark.asyncio
    async def test_publishes_stop_autopilot(self, engine):
        response = await stop_autopilot(engine)(_request())

        engine.bus.publish.assert_awaited_once_with(
            "SYSTEM_CONTROL", {"action": "STOP_AUTOPILOT"}, "HTTP"
        )
        assert response.status == 200

    @pytest.mark.asyncio
    async def test_publishes_nothing_else(self, engine):
        await stop_autopilot(engine)(_request())

        assert engine.bus.publish.await_count == 1
