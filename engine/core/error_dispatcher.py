"""
Centralized Error Handling System for Ghost Engine

This module provides the ErrorDispatcher class that standardizes error handling
across all agents and components.

Features:
- Error categorization by domain and severity
- Structured error logging to terminal
- Non-blocking SSE error broadcasting to frontend
- Error deduplication (prevents spam)
- Actionable error hints for users
- Error code tracking for analytics
"""
import asyncio
import hashlib
import traceback
from dataclasses import dataclass, field
from datetime import datetime

from core.error_codes import (
    ErrorCodes,
    ErrorDomain,
    ErrorSeverity,
    Colors
)


@dataclass
class ErrorEvent:
    """Structured error event for logging and broadcasting"""
    code: str                           # Error code (e.g., "INTELLIGENCE_AI_UNAVAILABLE")
    message: str                         # Human-readable error message
    severity: ErrorSeverity              # Error severity level
    domain: ErrorDomain                  # Error domain
    agent_name: str                      # Agent that raised the error
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    correlation_id: str | None = None  # For distributed tracing
    context: dict = field(default_factory=dict)  # Additional context
    hint: str | None = None           # Actionable hint for user
    stack_trace: str | None = None    # Stack trace (only for exceptions)

    def to_dict(self) -> dict:
        """Convert to dictionary for SSE broadcasting"""
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity.name,
            "domain": self.domain.value,
            "agent_name": self.agent_name,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
            "context": self.context,
            "hint": self.hint,
            "stack_trace": self.stack_trace
        }


class ErrorDispatcher:
    """
    Centralized error handling system

    Features:
    - Categorizes errors by domain and severity
    - Logs to terminal with colors
    - Broadcasts to frontend via SSE (non-blocking)
    - Deduplicates errors within 60 seconds
    - Provides actionable hints
    """

    # Error deduplication window (seconds)
    DEDUPLICATION_WINDOW = 60

    def __init__(self, agent_name: str, event_bus=None, synapse=None):
        """
        Initialize ErrorDispatcher

        Args:
            agent_name: Name of the agent (e.g., "BRAIN", "SENSES")
            event_bus: EventBus instance for broadcasting errors
            synapse: Optional Synapse instance for persistent error logging
        """
        self.agent_name = agent_name
        self.event_bus = event_bus
        self.synapse = synapse
        self._error_hashes = set()  # For deduplication
        self._error_timestamps = {}  # Hash -> timestamp

        # Lookup for error code hints
        self._code_lookup = {}
        for attr_name in dir(ErrorCodes):
            if not attr_name.startswith("_"):
                code, msg, hint = getattr(ErrorCodes, attr_name)
                self._code_lookup[code] = (msg, hint)

    def _get_error_info(self, code: str) -> tuple[str, str]:
        """Get error message and hint from error code"""
        if code in self._code_lookup:
            return self._code_lookup[code]
        return code, "Check system logs for details"

    def _generate_hash(self, code: str, message: str) -> str:
        """Generate MD5 hash for deduplication"""
        hash_input = f"{self.agent_name}:{code}:{message[:100]}"
        return hashlib.md5(hash_input.encode()).hexdigest()

    def _is_duplicate(self, error_hash: str) -> bool:
        """Check if error is duplicate within deduplication window"""
        now = datetime.now().timestamp()

        # Clean old hashes
        old_hashes = [
            h for h, ts in self._error_timestamps.items()
            if now - ts > self.DEDUPLICATION_WINDOW
        ]
        for h in old_hashes:
            del self._error_timestamps[h]
            self._error_hashes.discard(h)

        # Check if duplicate
        if error_hash in self._error_hashes:
            return True

        # Track new error
        self._error_hashes.add(error_hash)
        self._error_timestamps[error_hash] = now
        return False

    def _get_color(self, severity: ErrorSeverity) -> str:
        """Get terminal color for severity"""
        if severity == ErrorSeverity.CRITICAL:
            return Colors.RED
        if severity == ErrorSeverity.HIGH:
            return Colors.YELLOW
        if severity == ErrorSeverity.MEDIUM:
            return Colors.ORANGE
        if severity == ErrorSeverity.LOW:
            return Colors.BLUE
        return Colors.GRAY

    def _format_terminal_output(self, error: ErrorEvent) -> str:
        """Format error for terminal output"""
        color = self._get_color(error.severity)
        severity_str = error.severity.name

        parts = [
            f"{color}[{error.agent_name}][{severity_str}]{Colors.RESET}",
            f"{Colors.BOLD}{error.code}{Colors.RESET}",
            f"{error.message}"
        ]

        if error.hint:
            parts.append(f"\n{Colors.GRAY}  [!] Hint: {error.hint}{Colors.RESET}")

        if error.context:
            context_str = ", ".join(f"{k}={v}" for k, v in error.context.items())
            parts.append(f"\n{Colors.GRAY}  Context: {context_str}{Colors.RESET}")

        return " ".join(parts)

    async def dispatch(
        self,
        code: str,
        message: str | None = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        domain: ErrorDomain | None = None,
        context: dict | None = None,
        exception: Exception | None = None,
        hint: str | None = None
    ) -> ErrorEvent:
        """
        Dispatch an error to terminal and frontend

        Args:
            code: Error code from ErrorCodes class
            message: Override default error message
            severity: Error severity level
            domain: Error domain (auto-detected from code if not provided)
            context: Additional context dict
            exception: Exception object (for stack trace)
            hint: Override default hint

        Returns:
            ErrorEvent object
        """
        # Get default message and hint from code
        default_message, default_hint = self._get_error_info(code)
        final_message = message or default_message
        final_hint = hint or default_hint

        # Auto-detect domain from code if not provided
        if domain is None:
            code_prefix = code.split("_")[0] if "_" in code else "SYSTEM"
            try:
                domain = ErrorDomain[code_prefix]
            except (KeyError, ValueError):
                domain = ErrorDomain.SYSTEM

        # Create error event
        error = ErrorEvent(
            code=code,
            message=final_message,
            severity=severity,
            domain=domain,
            agent_name=self.agent_name,
            context=context or {},
            hint=final_hint,
            stack_trace=traceback.format_exc() if exception else None
        )

        # Check for deduplication
        error_hash = self._generate_hash(code, final_message)
        if self._is_duplicate(error_hash):
            # Still log locally but don't broadcast
            print(f"{Colors.GRAY}[{error.agent_name}] Duplicate error suppressed: {code}{Colors.RESET}")
            return error

        # Log to terminal
        print(self._format_terminal_output(error))

        # Broadcast to frontend via EventBus (non-blocking)
        if self.event_bus:
            asyncio.create_task(self._broadcast_error(error))

        # Log to Synapse if available
        if self.synapse:
            if error.severity.value >= ErrorSeverity.HIGH.value:
                # CRITICAL: Await for High/Critical errors to ensure "Error Box" halts the engine
                await self._log_to_synapse(error)
            else:
                # Non-critical: Fire-and-forget
                asyncio.create_task(self._log_to_synapse(error))

        return error

    async def _broadcast_error(self, error: ErrorEvent):
        """Broadcast error to frontend via EventBus"""
        try:
            if self.event_bus:
                await self.event_bus.publish(
                    "SYSTEM_ERROR",
                    error.to_dict(),
                    self.agent_name
                )
        except Exception as e:
            # Don't crash if broadcasting fails
            print(f"{Colors.RED}[ERROR_DISPATCHER] Failed to broadcast error: {e}{Colors.RESET}")

    async def _log_to_synapse(self, error: ErrorEvent):
        """Log error to Synapse for persistent storage"""
        try:
            from core.synapse import SynapseError
            if self.synapse:
                # Map ErrorEvent to SynapseError Pydantic model
                synapse_error = SynapseError(
                    agent_name=error.agent_name,
                    code=error.code,
                    message=error.message,
                    severity=error.severity.name,
                    domain=error.domain.value,
                    hint=error.hint,
                    context=error.context,
                    stack_trace=error.stack_trace
                )
                await self.synapse.errors.push(synapse_error)
        except Exception as e:
            print(f"{Colors.RED}[ERROR_DISPATCHER] Failed to log to Synapse: {e}{Colors.RESET}")

    def clear_history(self):
        """Clear error history (useful for testing)"""
        self._error_hashes.clear()
        self._error_timestamps.clear()
