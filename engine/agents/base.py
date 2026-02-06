from abc import ABC
from datetime import datetime
from typing import Any

from core.bus import EventBus
from core.error_dispatcher import ErrorDispatcher, ErrorDomain, ErrorSeverity
from core.error_manager import ErrorManager, get_error_manager
from core.synapse import Synapse


class BaseAgent(ABC):
    def __init__(self, name: str, agent_id: int, bus: EventBus, synapse: Synapse = None, error_manager: ErrorManager = None):
        self.name = name
        self.agent_id = agent_id
        self.bus = bus
        self.synapse = synapse
        # Use provided error_manager or get global instance
        self.error_manager = error_manager or get_error_manager()
        # Initialize centralized error dispatcher with error_manager
        self.error_dispatcher = ErrorDispatcher(
            agent_name=name,
            event_bus=bus,
            synapse=synapse,
            error_manager=self.error_manager
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
        """Log a message to both the bus (for frontend) and console."""
        from core.logger import get_logger
        
        # Publish to bus for Frontend
        payload = {
            "level": level,
            "message": message,
            "agent_id": self.agent_id,
            "agent_name": self.name,
            "timestamp": datetime.now().isoformat(),
        }
        await self.bus.publish("SYSTEM_LOG", payload, self.name)

        # Log to Console via Centralized Logger
        logger = get_logger(self.name)
        
        # Map log levels to logger methods
        log_methods = {
            "INFO": logger.info,
            "WARN": logger.warning,
            "WARNING": logger.warning,
            "ERROR": logger.error,
            "DEBUG": logger.debug,
            "SUCCESS": lambda msg: logger.info(f"SUCCESS: {msg}"),
        }
        
        log_func = log_methods.get(level, logger.info)
        log_func(message)

    async def log_error(
        self,
        code: str,
        message: str | None = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        domain: ErrorDomain | None = None,
        context: dict | None = None,
        exception: Exception | None = None,
        hint: str | None = None
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
