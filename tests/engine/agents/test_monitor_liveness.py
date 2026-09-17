"""The monitor loop is the only thing draining the opportunity queue.

Observed live: the loop logged "Found 1 opportunities. Processing batch..."
and was never heard from again. No traceback, no completion line. Nine
analysed-nothing opportunities sat in SQLite while /health reported the
engine fine, because asyncio stores an unretrieved task exception and says
nothing about it.

Two defects, both of which make a stopped loop indistinguishable from an
idle one:

  * Nothing observed the task, so a crash was silent.
  * stop_requested was passed as a bool, evaluated once when the task was
    created. The loop could never see a later STOP_AUTOPILOT, so the flag
    that exists to stop it did nothing.
"""

import asyncio

import pytest
from agents.brain.monitor import _should_stop


class TestStopFlagIsLive:
    def test_a_callable_is_re_read_each_time(self):
        """A bool snapshot is why STOP_AUTOPILOT never stopped the loop."""
        state = {"stop": False}

        def flag():
            return state["stop"]

        assert _should_stop(flag) is False
        state["stop"] = True
        assert _should_stop(flag) is True

    @pytest.mark.parametrize("value,expected", [(True, True), (False, False)])
    def test_plain_bools_still_work(self, value, expected):
        """Older call sites pass a bool; they must not break."""
        assert _should_stop(value) is expected

    def test_truthiness_is_normalised_to_bool(self):
        assert _should_stop(lambda: 1) is True
        assert _should_stop(lambda: None) is False


class TestMonitorDeathIsReported:
    @pytest.mark.asyncio
    async def test_a_crashed_monitor_is_logged_not_swallowed(self):
        """The regression: a dead loop looked exactly like an idle one."""
        from agents.brain.agent import BrainAgent

        logged: list[tuple[str, str]] = []

        async def fake_log(message, level="INFO"):
            logged.append((message, level))

        agent = BrainAgent.__new__(BrainAgent)
        agent.log = fake_log

        async def explode():
            raise RuntimeError("queue backend went away")

        task = asyncio.create_task(explode())
        task.add_done_callback(agent._on_monitor_exit)
        await asyncio.gather(task, return_exceptions=True)
        await asyncio.sleep(0)

        assert logged, "a dead monitor loop produced no log at all"
        message, level = logged[-1]
        assert level == "ERROR"
        assert "RuntimeError" in message
        assert "queue backend went away" in message

    @pytest.mark.asyncio
    async def test_a_clean_exit_is_still_worth_saying(self):
        """The loop is meant to run forever; returning is notable."""
        from agents.brain.agent import BrainAgent

        logged: list[tuple[str, str]] = []

        async def fake_log(message, level="INFO"):
            logged.append((message, level))

        agent = BrainAgent.__new__(BrainAgent)
        agent.log = fake_log

        async def finish():
            return None

        task = asyncio.create_task(finish())
        task.add_done_callback(agent._on_monitor_exit)
        await task
        await asyncio.sleep(0)

        assert logged
        assert logged[-1][1] == "WARN"

    @pytest.mark.asyncio
    async def test_cancellation_is_not_reported_as_a_crash(self):
        """Shutdown cancels the task; that is not a failure."""
        from agents.brain.agent import BrainAgent

        logged: list[tuple[str, str]] = []

        async def fake_log(message, level="INFO"):
            logged.append((message, level))

        agent = BrainAgent.__new__(BrainAgent)
        agent.log = fake_log

        async def forever():
            await asyncio.sleep(3600)

        task = asyncio.create_task(forever())
        await asyncio.sleep(0)
        task.add_done_callback(agent._on_monitor_exit)
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        await asyncio.sleep(0)

        assert logged == []
