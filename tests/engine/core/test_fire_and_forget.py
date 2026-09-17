"""Regression tests for firing async logs from synchronous code.

Several sync helpers report degraded conditions through an async log callback
via `asyncio.create_task`, which raises RuntimeError with no running loop. The
crash therefore replaced the degraded-path return value it was reporting --
notably the stale-market-data safety check, which raised instead of returning
STALE.
"""

import asyncio

import pytest

from core.shared_utils import fire_and_forget


def test_runs_coroutine_with_no_running_loop():
    """The original failure mode: sync context, no loop."""
    seen = []

    async def log(msg):
        seen.append(msg)

    fire_and_forget(log("hello"))
    assert seen == ["hello"]


@pytest.mark.asyncio
async def test_schedules_coroutine_when_loop_is_running():
    seen = []

    async def log(msg):
        seen.append(msg)

    fire_and_forget(log("hello"))
    await asyncio.sleep(0)  # let the scheduled task run
    assert seen == ["hello"]


def test_failing_coroutine_does_not_propagate():
    """Logging must never take down its caller."""

    async def boom():
        raise RuntimeError("log sink down")

    fire_and_forget(boom())  # must not raise


class TestFreshnessCheckSurvivesSyncContext:
    """The stale-opportunity guard rejects old market data. Both of its
    rejection paths logged via create_task, so both raised instead of
    returning STALE when called without a running loop."""

    @staticmethod
    def _check(opportunity):
        from agents.brain.monitor import check_opportunity_freshness

        async def log(msg, level="INFO"):
            return None

        return check_opportunity_freshness(opportunity, log)

    def test_stale_opportunity_returns_stale_not_crash(self):
        from datetime import datetime, timedelta

        from core.constants import BRAIN_STALE_OPPORTUNITY_SECONDS as STALE_AFTER

        old = (datetime.now() - timedelta(seconds=STALE_AFTER + 60)).isoformat()
        assert self._check({"ticker": "X", "timestamp": old}) == (False, "STALE")

    def test_missing_timestamp_returns_stale_not_crash(self):
        assert self._check({"ticker": "X"}) == (False, "STALE")

    def test_fresh_opportunity_still_accepted(self):
        from datetime import datetime

        now = datetime.now().isoformat()
        assert self._check({"ticker": "X", "timestamp": now}) == (True, "FRESH")
