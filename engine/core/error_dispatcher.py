"""
Centralized Error Handling System for Ghost Engine

This module provides the ErrorDispatcher class that standardizes error handling
across all agents and components. It provides:

- Error categorization by domain and severity
- Structured error logging to terminal
- Non-blocking SSE error broadcasting to frontend
- Error deduplication (prevents spam)
- Actionable error hints for users
- Error code tracking for analytics
"""

import asyncio
import hashlib
import os
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

# Windows-safe terminal colors
class Colors:
    """Terminal color codes (Windows-safe)"""
    RED = "\033[91m"      # CRITICAL
    YELLOW = "\033[93m"    # HIGH
    ORANGE = "\033[38;5;208m"  # MEDIUM
    BLUE = "\033[94m"      # LOW
    GRAY = "\033[90m"      # INFO
    GREEN = "\033[92m"     # SUCCESS
    RESET = "\033[0m"
    BOLD = "\033[1m"


class ErrorSeverity(Enum):
    """Error severity levels"""
    CRITICAL = 5  # System-wide failure, requires immediate intervention
    HIGH = 4      # Component failure, degrades service
    MEDIUM = 3    # Feature failure, workarounds available
    LOW = 2       # Minor issue, no impact on operations
    INFO = 1      # Informational, no error


class ErrorDomain(Enum):
    """Error domains by component"""
    NETWORK = "NETWORK"         # API connections, timeouts
    TRADING = "TRADING"         # Order execution, vault
    INTELLIGENCE = "INTELLIGENCE"  # AI services, Gemini
    DATA = "DATA"               # Queues, database, validation
    AUTH = "AUTH"               # Authentication, credentials
    CONFIG = "CONFIG"           # Environment, setup
    SYSTEM = "SYSTEM"           # General system errors


# Error Code Definitions
class ErrorCodes:
    """Standardized error codes with messages and hints"""

    # Network Errors (NETWORK_xxx)
    NETWORK_TIMEOUT = ("NETWORK_TIMEOUT", "API request timeout", "Check network connection")
    NETWORK_RATE_LIMIT = ("NETWORK_RATE_LIMIT", "API rate limit exceeded", "Wait before retrying")
    NETWORK_CONNECTION_FAILED = ("NETWORK_CONNECTION_FAILED", "Failed to connect to API", "Verify API credentials")
    NETWORK_SERVER_ERROR = ("NETWORK_SERVER_ERROR", "API server error", "Try again later")

    # Trading Errors (TRADING_xxx)
    TRADE_INSUFFICIENT_FUNDS = ("TRADE_INSUFFICIENT_FUNDS", "Insufficient vault balance", "Wait for order settlements")
    TRADE_KILL_SWITCH = ("TRADE_KILL_SWITCH", "Kill switch activated", "Manual intervention required")
    TRADE_INVALID_TICKER = ("TRADE_INVALID_TICKER", "Invalid market ticker", "Verify ticker symbol")
    TRADE_ORDER_FAILED = ("TRADE_ORDER_FAILED", "Order placement failed", "Check order parameters")
    TRADE_HARD_FLOOR = ("TRADE_HARD_FLOOR", "Balance below hard floor", "Emergency lockdown active")

    # Intelligence Errors (INTELLIGENCE_xxx)
    INTELLIGENCE_AI_UNAVAILABLE = ("INTELLIGENCE_AI_UNAVAILABLE", "AI service unavailable", "Check API key configuration")
    INTELLIGENCE_DEBATE_FAILED = ("INTELLIGENCE_DEBATE_FAILED", "AI debate failed", "System will veto trade")
    INTELLIGENCE_PARSE_ERROR = ("INTELLIGENCE_PARSE_ERROR", "Failed to parse AI response", "Response format invalid")
    INTELLIGENCE_TIMEOUT = ("INTELLIGENCE_TIMEOUT", "AI request timeout", "Service may be overloaded")

    # Data Errors (DATA_xxx)
    DATA_QUEUE_EMPTY = ("DATA_QUEUE_EMPTY", "No data in queue", "Waiting for new opportunities")
    DATA_VALIDATION_FAILED = ("DATA_VALIDATION_FAILED", "Data validation failed", "Check data format")
    DATA_PUSH_FAILED = ("DATA_PUSH_FAILED", "Failed to queue data", "Queue may be full")

    # Auth Errors (AUTH_xxx)
    AUTH_INVALID_KEY = ("AUTH_INVALID_KEY", "Invalid API credentials", "Check .env configuration")
    AUTH_MISSING_KEY = ("AUTH_MISSING_KEY", "API key not configured", "Set GEMINI_API_KEY in .env")

    # Config Errors (CONFIG_xxx)
    CONFIG_MISSING_ENV = ("CONFIG_MISSING_ENV", "Environment variable missing", "Check .env file")
    CONFIG_INVALID_VALUE = ("CONFIG_INVALID_VALUE", "Invalid configuration value", "Check config file")

    # System Errors (SYSTEM_xxx)
    SYSTEM_INIT_FAILED = ("SYSTEM_INIT_FAILED", "System initialization failed", "Check agent dependencies")
    SYSTEM_EVENT_BUS_FAILED = ("SYSTEM_EVENT_BUS_FAILED", "Event bus error", "Check agent subscriptions")


@dataclass
class ErrorEvent:
    """Structured error event for logging and broadcasting"""
    code: str                           # Error code (e.g., "INTELLIGENCE_AI_UNAVAILABLE")
    message: str                         # Human-readable error message
    severity: ErrorSeverity              # Error severity level
    domain: ErrorDomain                  # Error domain
    agent_name: str                      # Agent that raised the error
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    correlation_id: Optional[str] = None  # For distributed tracing
    context: dict = field(default_factory=dict)  # Additional context
    hint: Optional[str] = None           # Actionable hint for user
    stack_trace: Optional[str] = None    # Stack trace (only for exceptions)

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
        elif severity == ErrorSeverity.HIGH:
            return Colors.YELLOW
        elif severity == ErrorSeverity.MEDIUM:
            return Colors.ORANGE
        elif severity == ErrorSeverity.LOW:
            return Colors.BLUE
        else:
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
        message: Optional[str] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        domain: Optional[ErrorDomain] = None,
        context: Optional[dict] = None,
        exception: Optional[Exception] = None,
        hint: Optional[str] = None
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

        # Log to Synapse if available (non-blocking)
        if self.synapse:
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
            # TODO: Implement error logging to Synapse when error tables are added
            pass
        except Exception as e:
            print(f"{Colors.RED}[ERROR_DISPATCHER] Failed to log to Synapse: {e}{Colors.RESET}")

    def clear_history(self):
        """Clear error history (useful for testing)"""
        self._error_hashes.clear()
        self._error_timestamps.clear()


# Convenience functions for common error patterns
async def handle_ai_unavailable(dispatcher: ErrorDispatcher, agent_name: str, context: dict = None):
    """Handle AI service unavailable error"""
    return await dispatcher.dispatch(
        code="INTELLIGENCE_AI_UNAVAILABLE",
        severity=ErrorSeverity.HIGH,
        domain=ErrorDomain.INTELLIGENCE,
        context=context or {},
        hint="Check GEMINI_API_KEY in .env file"
    )


async def handle_api_error(dispatcher: ErrorDispatcher, status_code: int, context: dict = None):
    """Handle API error with status code"""
    if status_code == 429:
        return await dispatcher.dispatch(
            code="NETWORK_RATE_LIMIT",
            severity=ErrorSeverity.HIGH,
            domain=ErrorDomain.NETWORK,
            context=context or {}
        )
    elif 500 <= status_code <= 504:
        return await dispatcher.dispatch(
            code="NETWORK_SERVER_ERROR",
            severity=ErrorSeverity.MEDIUM,
            domain=ErrorDomain.NETWORK,
            context=context or {}
        )
    else:
        return await dispatcher.dispatch(
            code="NETWORK_CONNECTION_FAILED",
            severity=ErrorSeverity.HIGH,
            domain=ErrorDomain.NETWORK,
            context=context or {}
        )
