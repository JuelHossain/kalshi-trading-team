"""Ragnarok's lock-down must beat the flatten's own network round trips, and
its closes must not depend on the process-wide trading_mode flag.

trigger_ragnarok used to await execute_ragnarok() first and only set the
halt, disarm live placement and stop autopilot afterwards. execute_ragnarok
itself, when not pinned to paper, armed real order placement globally
(trading_mode.set_live(True)) for the whole cancel-and-close sequence. Two
races fell out of that:

1. A buy already queued (Brain approved it, Hand is about to place it) could
   reach KalshiClient.place_order while the flatten was still awaiting
   Kalshi. Nothing halted it yet, and the global flag was armed, so a
   paper-approved signal went out as a real order -- reproduced in the audit
   as a genuine POST to /portfolio/events/orders while the operator believed
   the engine was in paper mode.

2. In the other direction, a paper cycle starting mid-flatten (an autopilot
   pulse, or a /trigger click) calls trading_mode.set_live(False) before it
   is even authorised (engine/main.py, execute_single_cycle). If that landed
   between execute_ragnarok's own network calls, Ragnarok's own closes read
   the now-False global flag and became simulated paper fills: the real
   position stayed open on Kalshi, Ragnarok reported "closed N/N", and the
   paper book gained a phantom holding nobody traded.

A follow-up review then found two regressions in the fix itself: moving
`executions.clear()` ahead of the flatten meant a raising clear (a locked or
full database) skipped the flatten entirely, and moving only one
`set_live(False)` ahead of the flatten left the engine armed if something
re-armed it mid-flatten (a live cycle authorised just before Ragnarok was
pressed). The two extra test classes below cover those.

The tests below use a `request()` stub with a real await (asyncio.sleep) so
the event loop genuinely interleaves the racing coroutine partway through
the flatten -- this is not just checking source order, it drives the actual
concurrent execution.
"""

import asyncio
import sqlite3
from types import SimpleNamespace

import pytest
from core import trading_mode
from core.network import KalshiClient
from core.synapse import Synapse


async def _noop_publish(*_args, **_kwargs):
    """trigger_ragnarok only awaits engine.bus.publish; it never inspects
    what it returns."""
    return None


def _fake_engine(synapse):
    """A minimal stand-in for GhostEngine, just what trigger_ragnarok touches."""
    return SimpleNamespace(
        manual_kill_switch=False,
        bus=SimpleNamespace(publish=_noop_publish),
        synapse=synapse,
    )


class TestABuyRacingTheFlattenIsRefused:
    """Rs0+Rm0+Rs1: the lock-down (halt, disarm, STOP_AUTOPILOT, drop
    approvals) must be in force before execute_ragnarok is ever awaited, not
    after it returns -- otherwise a buy that lands mid-flatten sees no halt
    at all."""

    @pytest.mark.asyncio
    async def test_a_buy_in_flight_during_the_route_is_refused_not_posted(
        self, monkeypatch, tmp_path
    ):
        from http_api.routes import trigger_ragnarok

        monkeypatch.setenv("IS_PAPER_TRADING", "false")
        trading_mode.set_live(False)  # the state a paper cycle leaves behind

        import core.safety

        sent = []
        client = KalshiClient.__new__(KalshiClient)

        async def request(method, path, json_data=None, **_kwargs):
            # A real await, so the event loop can run the racing buy while
            # this is in flight -- not a plain function call that runs to
            # completion without ever yielding control.
            await asyncio.sleep(0.03)
            sent.append((method, path, json_data))
            if method == "GET" and path == "/portfolio/orders":
                return {"orders": []}
            if method == "GET" and path == "/portfolio/positions":
                return {"market_positions": []}
            return {"order_id": "should-not-happen"}

        client.request = request
        monkeypatch.setattr(core.safety, "kalshi_client", client)

        synapse = Synapse(db_path=str(tmp_path / "race.db"))
        engine = _fake_engine(synapse)

        try:
            ragnarok_task = asyncio.create_task(trigger_ragnarok(engine)(None))
            buy_task = asyncio.create_task(
                client.place_order("KXNEW", "yes", "limit", 45, 10, action="buy")
            )

            with pytest.raises(RuntimeError, match="halted"):
                await buy_task
            await ragnarok_task
        finally:
            synapse.close()

        posts = [(m, p) for (m, p, _) in sent if m == "POST"]
        assert posts == [], "a buy must never reach Kalshi while Ragnarok is flattening"


class TestClosesSurviveAConcurrentDisarm:
    """Rs1: a concurrent trading_mode.set_live(False) -- what a paper cycle
    does before it is even authorised -- must not turn Ragnarok's own close
    into a paper fill."""

    @pytest.mark.asyncio
    async def test_a_disarm_mid_flatten_does_not_paper_fill_the_close(self, monkeypatch):
        from core.safety import execute_ragnarok

        monkeypatch.setenv("IS_PAPER_TRADING", "false")
        trading_mode.set_live(False)  # paper autopilot was the last thing to run

        import core.safety

        sent = []
        client = KalshiClient.__new__(KalshiClient)

        async def request(method, path, json_data=None, **_kwargs):
            await asyncio.sleep(0.03)
            if method == "GET" and path == "/portfolio/orders":
                return {"orders": []}
            if method == "GET" and path == "/portfolio/positions":
                return {"market_positions": [{"ticker": "KXREAL", "position": 3}]}
            if method == "GET" and path.endswith("/orderbook"):
                return None
            sent.append((method, path, json_data))
            return {"order_id": "closed-1"}

        client.request = request
        monkeypatch.setattr(core.safety, "kalshi_client", client)

        async def disarm_mid_flatten():
            # Shorter than the stub's own latency, so this always lands
            # before close_one ever checks trading_mode.is_live().
            await asyncio.sleep(0.005)
            trading_mode.set_live(False)

        disarm_task = asyncio.create_task(disarm_mid_flatten())
        result = await execute_ragnarok()
        await disarm_task

        assert result["positions_closed"] == 1
        posts = [(m, p) for (m, p, _) in sent if m == "POST"]
        assert posts == [
            ("POST", "/portfolio/events/orders")
        ], "the close must reach Kalshi for real, not become a simulated fill"
        assert trading_mode.paper_positions() == [], "no phantom paper position from the close"


class TestAFailedQueueClearDoesNotBlockTheFlatten:
    """Rs0+Rm0+Rs1 (round 2): reordering trigger_ragnarok to lock down before
    the flatten must not make a failing `executions.clear()` cancel the
    flatten. Synapse.clear() is a plain SQLite DELETE with no retry -- "database
    or disk is full", a lock held past sqlite's busy timeout, or a closed
    connection all raise. None of those may stop a single cancel or close
    from reaching Kalshi."""

    @pytest.mark.asyncio
    async def test_a_raising_clear_still_lets_the_close_reach_kalshi(self, monkeypatch):
        from http_api.routes import trigger_ragnarok

        monkeypatch.setenv("IS_PAPER_TRADING", "false")
        trading_mode.set_live(False)  # the state a paper cycle leaves behind

        import core.safety

        sent = []
        client = KalshiClient.__new__(KalshiClient)

        async def request(method, path, json_data=None, **_kwargs):
            if method == "GET" and path == "/portfolio/orders":
                return {"orders": []}
            if method == "GET" and path == "/portfolio/positions":
                return {"market_positions": [{"ticker": "KXREAL", "position": 3}]}
            if method == "GET" and path.endswith("/orderbook"):
                return None
            sent.append((method, path, json_data))
            return {"order_id": "closed-1"}

        client.request = request
        monkeypatch.setattr(core.safety, "kalshi_client", client)

        async def raising_clear():
            raise sqlite3.OperationalError("database or disk is full")

        engine = SimpleNamespace(
            manual_kill_switch=False,
            bus=SimpleNamespace(publish=_noop_publish),
            synapse=SimpleNamespace(executions=SimpleNamespace(clear=raising_clear)),
        )

        response = await trigger_ragnarok(engine)(None)

        posts = [(m, p) for (m, p, _) in sent if m == "POST"]
        assert posts == [
            ("POST", "/portfolio/events/orders")
        ], "the reduce-only close must reach Kalshi even though the queue clear failed"
        assert "dropped unknown" in response.text


class TestLiveEndsDisarmedEvenIfReArmedMidFlatten:
    """Rs0+Rm0+Rs1 (round 2): a concurrent trading_mode.set_live(True) landing
    mid-flatten -- e.g. a live cycle authorised (main.py) just before
    Ragnarok was pressed -- must not leave the engine armed once the route
    returns. Only setting set_live(False) before the flatten is not enough;
    it must be set again after."""

    @pytest.mark.asyncio
    async def test_a_mid_flatten_rearm_does_not_survive_the_route(self, monkeypatch, tmp_path):
        from http_api.routes import trigger_ragnarok

        monkeypatch.setenv("IS_PAPER_TRADING", "false")
        trading_mode.set_live(False)

        import core.safety

        client = KalshiClient.__new__(KalshiClient)

        async def request(method, path, json_data=None, **_kwargs):
            await asyncio.sleep(0.03)
            if method == "GET" and path == "/portfolio/orders":
                return {"orders": []}
            if method == "GET" and path == "/portfolio/positions":
                return {"market_positions": [{"ticker": "KXREAL", "position": 3}]}
            if method == "GET" and path.endswith("/orderbook"):
                return None
            return {"order_id": "closed-1"}

        client.request = request
        monkeypatch.setattr(core.safety, "kalshi_client", client)

        synapse = Synapse(db_path=str(tmp_path / "rearm.db"))
        engine = _fake_engine(synapse)

        async def rearm_mid_flatten():
            # Simulates main.py authorising a live cycle a few ms into the
            # flatten (main.py:477 calls set_live(True) after authorization).
            await asyncio.sleep(0.005)
            trading_mode.set_live(True)

        try:
            rearm_task = asyncio.create_task(rearm_mid_flatten())
            await trigger_ragnarok(engine)(None)
            await rearm_task
        finally:
            synapse.close()

        assert (
            trading_mode.is_live() is False
        ), "Ragnarok must end disarmed even if something re-armed live mid-flatten"
