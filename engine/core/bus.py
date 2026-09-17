import asyncio
import contextvars
from collections import deque
from collections.abc import Callable
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field
from core.display import log_error, AgentType

# Sensitive patterns to mask in logs
SENSITIVE_KEYS = {"api_key", "secret", "private_key", "password", "token", "signature"}


class Message(BaseModel):
    topic: str
    payload: dict[str, Any]
    sender: str
    timestamp: datetime = Field(default_factory=datetime.now)

    def to_json(self) -> str:
        return self.model_dump_json()


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


class EventBus:
    """
    Asynchronous JSON Message Bus.
    The Central Nervous System of the Ghost Engine.
    """

    def __init__(self):
        self.subscribers: dict[str, list[Callable[[Message], Any]]] = {}
        self.history: deque[Message] = deque(maxlen=1000)  # Short-term memory with auto-trim
        self._lock = asyncio.Lock()
        # Re-entrant publishes refused. Non-zero means a subscriber is
        # publishing the topic it handles; see publish().
        self.reentrant_drops = 0

    async def subscribe(self, topic: str, callback: Callable[[Message], Any]):
        async with self._lock:
            if topic not in self.subscribers:
                self.subscribers[topic] = []
            self.subscribers[topic].append(callback)
        # We don't print to stdout here to keep logs clean, or we mask it
        # print(f"[BUS] Subscriber added to {topic}")

    async def publish(self, topic: str, payload: dict[str, Any], sender: str):
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

        async with self._lock:
            self.history.append(msg)  # Auto-trims when maxlen exceeded

        if topic in self.subscribers:
            token = _dispatching.set(active | {topic})
            try:
                # Dispatch to all subscribers in parallel
                tasks = [
                    self._safe_dispatch(callback, msg)
                    for callback in self.subscribers[topic]
                ]
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

    def get_history(self) -> list[Message]:
        return self.history
