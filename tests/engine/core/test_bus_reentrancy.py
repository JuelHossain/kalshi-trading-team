"""A subscriber that publishes its own topic must not hang the bus.

EventBus.publish awaits every subscriber. If one of them publishes the same
topic, the outer publish waits on the inner, which waits on the next. Each
level runs as a fresh gathered task, so no RecursionError fires -- the
publisher simply never returns.

The Gateway did this for SIM_RESULT, SYSTEM_HEALTH and SYSTEM_ERROR. The
Brain's next await after "AI Prob: ..." is a SIM_RESULT publish; no decision
was ever logged after it, and the engine reported healthy throughout.
"""
import asyncio

import pytest

from core.bus import EventBus


@pytest.fixture
def bus():
    return EventBus()


class TestReentrantPublishIsDropped:
    @pytest.mark.asyncio
    async def test_a_self_republishing_subscriber_does_not_hang(self, bus):
        """The regression. Without the guard this never returns."""
        calls = []

        async def echo(msg):
            calls.append(msg.payload["n"])
            await bus.publish("PING", {"n": msg.payload["n"] + 1}, "echo")

        await bus.subscribe("PING", echo)

        await asyncio.wait_for(bus.publish("PING", {"n": 0}, "test"), timeout=2)

        assert calls == [0], "the subscriber ran more than once"
        assert bus.reentrant_drops == 1

    @pytest.mark.asyncio
    async def test_the_drop_is_counted_so_it_can_be_seen(self, bus):
        async def echo(msg):
            await bus.publish("T", {}, "echo")

        await bus.subscribe("T", echo)
        assert bus.reentrant_drops == 0

        await asyncio.wait_for(bus.publish("T", {}, "test"), timeout=2)

        assert bus.reentrant_drops == 1

    @pytest.mark.asyncio
    async def test_indirect_loops_are_caught_too(self, bus):
        """A -> B -> A is the same hang with one more hop."""
        seen = []

        async def on_a(msg):
            seen.append("A")
            await bus.publish("B", {}, "a")

        async def on_b(msg):
            seen.append("B")
            await bus.publish("A", {}, "b")

        await bus.subscribe("A", on_a)
        await bus.subscribe("B", on_b)

        await asyncio.wait_for(bus.publish("A", {}, "test"), timeout=2)

        assert seen == ["A", "B"]
        assert bus.reentrant_drops == 1


class TestLegitimatePublishingStillWorks:
    @pytest.mark.asyncio
    async def test_a_subscriber_may_publish_a_different_topic(self, bus):
        """The guard must not block ordinary fan-out."""
        got = []

        async def on_first(msg):
            await bus.publish("SECOND", {"from": "first"}, "first")

        async def on_second(msg):
            got.append(msg.payload["from"])

        await bus.subscribe("FIRST", on_first)
        await bus.subscribe("SECOND", on_second)

        await bus.publish("FIRST", {}, "test")

        assert got == ["first"]
        assert bus.reentrant_drops == 0

    @pytest.mark.asyncio
    async def test_sequential_publishes_of_one_topic_are_not_reentrant(self, bus):
        """Only nesting is the problem, not repetition."""
        count = 0

        async def handler(msg):
            nonlocal count
            count += 1

        await bus.subscribe("T", handler)

        for _ in range(3):
            await bus.publish("T", {}, "test")

        assert count == 3
        assert bus.reentrant_drops == 0

    @pytest.mark.asyncio
    async def test_the_guard_is_released_after_dispatch(self, bus):
        """A topic must be publishable again once its dispatch completes."""
        async def noop(msg):
            pass

        await bus.subscribe("T", noop)
        await bus.publish("T", {}, "test")
        await bus.publish("T", {}, "test")

        assert bus.reentrant_drops == 0

    @pytest.mark.asyncio
    async def test_the_guard_is_released_even_if_a_subscriber_raises(self, bus):
        async def boom(msg):
            raise RuntimeError("subscriber failed")

        await bus.subscribe("T", boom)
        await bus.publish("T", {}, "test")
        await bus.publish("T", {}, "test")

        assert bus.reentrant_drops == 0

    @pytest.mark.asyncio
    async def test_sibling_subscribers_do_not_see_each_other_as_reentrant(self, bus):
        """Two handlers of X both publishing Y is fan-out, not a loop."""
        got = []

        async def on_y(msg):
            got.append(msg.sender)

        async def on_x_1(msg):
            await bus.publish("Y", {}, "x1")

        async def on_x_2(msg):
            await bus.publish("Y", {}, "x2")

        await bus.subscribe("Y", on_y)
        await bus.subscribe("X", on_x_1)
        await bus.subscribe("X", on_x_2)

        await bus.publish("X", {}, "test")

        assert sorted(got) == ["x1", "x2"]
        assert bus.reentrant_drops == 0
