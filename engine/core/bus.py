import asyncio
from typing import Dict, List, Callable, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import json
import re

# Sensitive patterns to mask in logs
SENSITIVE_KEYS = {"api_key", "secret", "private_key", "password", "token", "signature"}

class Message(BaseModel):
    topic: str
    payload: Dict[str, Any]
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
    elif isinstance(data, list):
        return [mask_sensitives(i) for i in data]
    return data

class EventBus:
    """
    Asynchronous JSON Message Bus.
    The Central Nervous System of the Ghost Engine.
    """
    def __init__(self):
        self.subscribers: Dict[str, List[Callable[[Message], Any]]] = {}
        self.history: List[Message] = [] # Short-term memory
        self._lock = asyncio.Lock()

    async def subscribe(self, topic: str, callback: Callable[[Message], Any]):
        async with self._lock:
            if topic not in self.subscribers:
                self.subscribers[topic] = []
            self.subscribers[topic].append(callback)
        # We don't print to stdout here to keep logs clean, or we mask it
        # print(f"[BUS] Subscriber added to {topic}")

    async def publish(self, topic: str, payload: Dict[str, Any], sender: str):
        # Mask sensitive data before creating the message if it's a log
        if topic == "SYSTEM_LOG":
            payload = mask_sensitives(payload)

        try:
            msg = Message(topic=topic, payload=payload, sender=sender)
        except Exception as e:
            print(f"[BUS][ERROR] Failed to validate message for {topic}: {e}")
            return

        async with self._lock:
            self.history.append(msg)
            # Keep history light (last 1000 messages)
            if len(self.history) > 1000:
                self.history.pop(0)

        if topic in self.subscribers:
            # Dispatch to all subscribers in parallel
            tasks = []
            for callback in self.subscribers[topic]:
                tasks.append(self._safe_dispatch(callback, msg))
            
            if tasks:
                await asyncio.gather(*tasks)

    async def _safe_dispatch(self, callback: Callable[[Message], Any], msg: Message):
        """Wrapper to prevent one failing subscriber from crashing the bus."""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(msg)
            else:
                callback(msg)
        except Exception as e:
            print(f"[BUS][ERROR] Callback failed for topic {msg.topic}: {e}")

    def get_history(self) -> List[Message]:
        return self.history
