import json
import os
from abc import ABC
from datetime import datetime
from typing import Any, Optional

from core.bus import EventBus
from core.synapse import Synapse
from core.error_dispatcher import ErrorDispatcher, ErrorSeverity, ErrorDomain


class BaseAgent(ABC):
    def __init__(self, name: str, agent_id: int, bus: EventBus, synapse: Synapse = None):
        self.name = name
        self.agent_id = agent_id
        self.bus = bus
        self.synapse = synapse
        # Initialize centralized error dispatcher
        self.error_dispatcher = ErrorDispatcher(
            agent_name=name,
            event_bus=bus,
            synapse=synapse
        )

    async def start(self):
        """Standard entry point. Override if custom logic needed before TICK."""
        await self.setup()
        await self.bus.subscribe("TICK", self._handle_tick_internal)

    async def setup(self):
        """Standard setup logic."""

    async def teardown(self):
        """Standard cleanup logic."""

    async def _handle_tick_internal(self, message):
        from core.db import send_heartbeat

        await send_heartbeat(self.agent_id, self.name)
        await self.on_tick(message.payload)

    async def on_tick(self, payload: Any):
        """Handler for periodic ticks."""

    async def log(self, message: str, level: str = "INFO"):
        # Filter emojis for Windows console compatibility
        import re
        emoji_pattern = re.compile("["
            u"\U0001F600-\U0001F64F"  # emoticons
            u"\U0001F300-\U0001F5FF"  # symbols & pictographs
            u"\U0001F680-\U0001F6FF"  # transport & map symbols
            u"\U0001F1E0-\U0001F1FF"  # flags
            u"\U00002702-\U000027B0"
            u"\U000024C2-\U0001F251"
            "]+", flags=re.UNICODE)
        clean_message = emoji_pattern.sub(r'', message)

        payload = {
            "level": level,
            "message": message,  # Keep original message for frontend
            "agent_id": self.agent_id,
            "agent_name": self.name,
            "timestamp": datetime.now().isoformat(),
        }
        await self.bus.publish("SYSTEM_LOG", payload, self.name)

        if os.getenv("JSON_LOGS") == "true":
            print(json.dumps({"type": "LOG", "data": payload}))
        else:
            print(f"[{self.name}] {clean_message}")

    async def log_error(
        self,
        code: str,
        message: Optional[str] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        domain: Optional[ErrorDomain] = None,
        context: Optional[dict] = None,
        exception: Optional[Exception] = None,
        hint: Optional[str] = None
    ):
        """
        Log an error using the centralized error dispatcher

        Args:
            code: Error code from ErrorCodes class (e.g., "INTELLIGENCE_AI_UNAVAILABLE")
            message: Override default error message
            severity: Error severity level (default: MEDIUM)
            domain: Error domain (auto-detected from code if not provided)
            context: Additional context dict
            exception: Exception object (for stack trace)
            hint: Override default hint

        Example:
            await self.log_error(
                code="INTELLIGENCE_AI_UNAVAILABLE",
                context={"ticker": ticker},
                exception=e
            )
        """
        return await self.error_dispatcher.dispatch(
            code=code,
            message=message,
            severity=severity,
            domain=domain,
            context=context,
            exception=exception,
            hint=hint
        )
