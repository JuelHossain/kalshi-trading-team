from abc import ABC, abstractmethod
from typing import Any
import json
import os
from datetime import datetime
from core.bus import EventBus, Message


class BaseAgent(ABC):
    def __init__(self, name: str, agent_id: int, bus: EventBus):
        self.name = name
        self.agent_id = agent_id
        self.bus = bus

    async def start(self):
        """Standard entry point. Override if custom logic needed before TICK."""
        await self.setup()
        await self.bus.subscribe("TICK", self._handle_tick_internal)

    async def setup(self):
        """Standard setup logic."""
        pass

    async def teardown(self):
        """Standard cleanup logic."""
        pass

    async def _handle_tick_internal(self, message):
        from core.db import send_heartbeat

        await send_heartbeat(self.agent_id, self.name)
        await self.on_tick(message.payload)

    async def on_tick(self, payload: Any):
        """Handler for periodic ticks."""
        pass

    async def log(self, message: str, level: str = "INFO"):
        payload = {
            "level": level,
            "message": message,
            "agent_id": self.agent_id,
            "agent_name": self.name,
            "timestamp": datetime.now().isoformat(),
        }
        await self.bus.publish("SYSTEM_LOG", payload, self.name)

        if os.getenv("JSON_LOGS") == "true":
            print(json.dumps({"type": "LOG", "data": payload}))
        else:
            print(f"[{self.name}] {message}")
