"""The in-process event bus every agent talks through.

publish() delivers one Message to every subscriber of its topic and awaits
them all, so a publisher inherits its subscribers' runtime. Two rules
follow from that and are enforced here: sensitive keys in SYSTEM_LOG
payloads are masked before delivery, and a publish of topic X issued from
inside X's own dispatch is dropped and counted rather than allowed to
recurse forever.
"""

import asyncio
import contextvars
from collections.abc import Callable
from datetime import datetime
from typing import Any

from core.display import AgentType, log_error
from pydantic import BaseModel, Field

# Sensitive patterns to mask in logs
SENSITIVE_KEYS = {"api_key", "secret", "private_key", "password", "token", "signature"}


class Message(BaseModel):
    """One event on the bus: topic, payload, sender and timestamp."""

    topic: str
    payload: dict[str, Any]
    sender: str
    timestamp: datetime = Field(default_factory=datetime.now)


def mask_sensitives(data: Any) -> Any:
    """Recursively mask sensitive keys in a dictionary or list."""
    if isinstance(data, dict):
        return {
            k: ("********" if any(s in k.lower() for s in SENSITIVE_KEYS) else mask_sensitives(v))
            for k, v in data.items()
        }
    if isinstance(data, list):
        return [mask_sensitives(i) for i in data]
    return data


# Topics whose dispatch is in progress somewhere up the current task tree.
# A frozenset, replaced rather than mutated: asyncio copies the Context into
# each gathered task, and a shared mutable set would leak across siblings.
_dispatching: contextvars.ContextVar[frozenset[str]] = contextvars.ContextVar(
    "eventbus_dispatching", default=frozenset()
)


def detached_context() -> contextvars.Context:
    """A copy of the current Context with no dispatch in progress.

    A task inherits its creator's Context, so a task spawned from inside a
    subscriber carries that dispatch's topics for its whole life -- long after
    the dispatch has returned -- and any publish of those topics from it is
    dropped as re-entrant. A detached task is never awaited by the dispatch
    that spawned it, so it cannot deadlock it; it must start clean. This is
    what stalled autopilot: the cycle is detached from REQUEST_CYCLE's
    dispatch, and the next REQUEST_CYCLE from inside it was dropped.
    """
    ctx = contextvars.copy_context()
    ctx.run(_dispatching.set, frozenset())
    return ctx


class EventBus:
    """
    Asynchronous JSON Message Bus.
    The Central Nervous System of the Ghost Engine.
    """

    def __init__(self):
        self.subscribers: dict[str, list[Callable[[Message], Any]]] = {}
        # Re-entrant publishes refused. Non-zero means a subscriber is
        # publishing the topic it handles; see publish().
        self.reentrant_drops = 0

    async def subscribe(self, topic: str, callback: Callable[[Message], Any]):
        """Register `callback` for `topic`. Callbacks may be sync or async."""
        if topic not in self.subscribers:
            self.subscribers[topic] = []
        self.subscribers[topic].append(callback)
        # We don't print to stdout here to keep logs clean, or we mask it
        # print(f"[BUS] Subscriber added to {topic}")

    async def publish(self, topic: str, payload: dict[str, Any], sender: str):
        """Deliver one event to every subscriber, awaiting each; see the re-entrancy note below."""
        # Mask sensitive data before creating the message if it's a log
        if topic == "SYSTEM_LOG":
            payload = mask_sensitives(payload)

        try:
            msg = Message(topic=topic, payload=payload, sender=sender)
        except Exception as e:
            log_error(f"Failed to validate message for {topic}: {e}", AgentType.SOUL)
            return

        # Refuse to re-enter a topic from inside its own dispatch.
        #
        # publish awaits every subscriber. If a subscriber publishes the same
        # topic, this call cannot complete until that nested call completes,
        # which cannot complete until *its* nested call does. Each level runs
        # as a fresh gathered task, so the recursion limit never trips and no
        # error is raised: the publisher simply never returns. The Gateway
        # did exactly this for three topics, and it froze the Brain's queue
        # loop with the engine reporting healthy.
        #
        # Dropping the nested publish and saying so is the only safe answer.
        # The outer dispatch already delivers this event to every subscriber.
        active = _dispatching.get()
        if topic in active:
            self.reentrant_drops += 1
            log_error(
                f"Dropped re-entrant publish of {topic} from {sender}: a "
                f"subscriber to {topic} is publishing {topic}. That would never "
                f"return. Fix the subscriber.",
                AgentType.SOUL,
            )
            return

        if topic in self.subscribers:
            token = _dispatching.set(active | {topic})
            try:
                # Dispatch to all subscribers in parallel
                tasks = [self._safe_dispatch(callback, msg) for callback in self.subscribers[topic]]
                if tasks:
                    await asyncio.gather(*tasks)
            finally:
                _dispatching.reset(token)

    async def _safe_dispatch(self, callback: Callable[[Message], Any], msg: Message):
        """Wrapper to prevent one failing subscriber from crashing the bus."""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(msg)
            else:
                callback(msg)
        except Exception as e:
            log_error(f"Callback failed for topic {msg.topic}: {e}", AgentType.SOUL)
