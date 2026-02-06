"""
Centralized Error Management System for Ghost Engine

This module provides the ErrorManager class that serves as the single source of truth
for all error handling in the Ghost Engine. It can stop the engine on critical errors,
track errors by agent and severity, and provide beautiful error displays using Rich.

Features:
- Single Source of Truth: All errors route through one central handler
- Engine Shutdown Capability: Can stop the entire engine on critical errors
- Error Tracking: Track errors by agent, severity, and frequency
- Beautiful Error Display: Uses Rich for error output (panels, colors, context)
- Error Recovery: Optional retry logic with configurable max attempts
- Error Logging: Log all errors with full context and stack traces
- No Mock Fallbacks: All errors are real, actionable errors
"""
import asyncio
import sys
import traceback
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Awaitable, Callable, Coroutine

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from core.error_codes import ErrorDomain, ErrorSeverity


class ErrorAction(Enum):
    """Actions that can be taken when an error occurs"""
    LOG_ONLY = "log_only"           # Just log the error
    RETRY = "retry"                 # Retry the operation
    SHUTDOWN = "shutdown"           # Shutdown the engine
    RECOVER = "recover"             # Attempt recovery


@dataclass
class ErrorRecord:
    """A record of an error that occurred"""
    code: str
    message: str
    severity: ErrorSeverity
    domain: ErrorDomain
    agent_name: str
    timestamp: datetime = field(default_factory=datetime.now)
    context: dict = field(default_factory=dict)
    stack_trace: str | None = None
    hint: str | None = None
    retry_count: int = 0
    resolved: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity.name,
            "domain": self.domain.value,
            "agent_name": self.agent_name,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context,
            "stack_trace": self.stack_trace,
            "hint": self.hint,
            "retry_count": self.retry_count,
            "resolved": self.resolved,
        }


class ErrorManager:
    """
    Centralized Error Management System

    This is the single source of truth for all error handling in the Ghost Engine.
    It provides:
    - Centralized error registration and tracking
    - Engine shutdown on critical errors
    - Error statistics and analytics
    - Beautiful error display with Rich
    - Retry logic with configurable attempts
    - Comprehensive logging with context
    """

    def __init__(
        self,
        shutdown_callback: Callable[[str], Awaitable[None]] | None = None,
        console: Console | None = None,
        max_retry_attempts: int = 3,
        retry_delay: float = 1.0,
    ):
        """
        Initialize the ErrorManager

        Args:
            shutdown_callback: Async callback to invoke when engine needs to shutdown
            console: Rich Console instance for beautiful output
            max_retry_attempts: Maximum number of retry attempts for recoverable errors
            retry_delay: Delay between retry attempts in seconds
        """
        self.shutdown_callback = shutdown_callback
        self.console = console or Console()
        self.max_retry_attempts = max_retry_attempts
        self.retry_delay = retry_delay

        # Error tracking
        self._errors: list[ErrorRecord] = []
        self._error_counts: defaultdict[tuple[str, str], int] = defaultdict(int)  # (agent, code) -> count

        # Recovery handlers
        self._recovery_handlers: dict[str, Callable[[], Awaitable[bool]]] = {}

        # Engine state
        self._is_shutting_down = False

    async def register_error(
        self,
        code: str,
        message: str,
        severity: ErrorSeverity,
        domain: ErrorDomain,
        agent_name: str,
        context: dict | None = None,
        exception: Exception | None = None,
        hint: str | None = None,
        stack_trace: str | None = None,
    ) -> ErrorRecord:
        """
        Register an error with the central error manager

        This is the MAIN ENTRY POINT for all errors in the system.
        All errors should route through this method.

        Args:
            code: Error code (e.g., "INTELLIGENCE_AI_UNAVAILABLE")
            message: Human-readable error message
            severity: Error severity level
            domain: Error domain
            agent_name: Name of the agent that raised the error
            context: Additional context dictionary
            exception: Exception object (for stack trace)
            hint: Actionable hint for resolution
            stack_trace: Custom stack trace (if not from exception)

        Returns:
            ErrorRecord object
        """
        if self._is_shutting_down:
            # Don't process new errors during shutdown
            return ErrorRecord(
                code=code,
                message=message,
                severity=severity,
                domain=domain,
                agent_name=agent_name,
            )

        # Generate stack trace from exception if not provided
        if exception and not stack_trace:
            stack_trace = "".join(traceback.format_exception(
                type(exception), exception, exception.__traceback__
            ))

        # Create error record
        error_record = ErrorRecord(
            code=code,
            message=message,
            severity=severity,
            domain=domain,
            agent_name=agent_name,
            context=context or {},
            stack_trace=stack_trace,
            hint=hint,
        )

        # Store error
        self._errors.append(error_record)
        self._error_counts[(agent_name, code)] += 1

        # Display error
        self._display_error(error_record)

        # Handle based on severity
        if severity == ErrorSeverity.CRITICAL:
            await self.handle_critical(error_record)
        elif severity == ErrorSeverity.HIGH:
            await self.handle_high(error_record)
        else:
            await self.handle_warning(error_record)

        return error_record

    async def handle_critical(self, error: ErrorRecord) -> None:
        """
        Handle a critical error by shutting down the engine

        Critical errors represent system-wide failures that require immediate
        intervention. The engine will be shut down gracefully.

        Args:
            error: The critical error to handle
        """
        self.console.print("\n")
        self.console.print(
            Panel(
                f"[red bold]CRITICAL ERROR DETECTED[/red bold]\n\n"
                f"[red]Agent: {error.agent_name}[/red]\n"
                f"[red]Error: {error.code}[/red]\n"
                f"[red]Message: {error.message}[/red]\n\n"
                f"[yellow]Initiating emergency engine shutdown...[/yellow]",
                title="[red bold]ENGINE SHUTDOWN[/red bold]",
                border_style="red",
                padding=(1, 2),
            )
        )

        self._is_shutting_down = True

        # Invoke shutdown callback if provided
        if self.shutdown_callback:
            try:
                await self.shutdown_callback(str(error.message))
            except Exception as e:
                self.console.print(
                    f"[red]Error during shutdown callback: {e}[/red]"
                )

    async def handle_high(self, error: ErrorRecord) -> None:
        """
        Handle a high-severity error

        High-severity errors represent component failures that degrade service.
        These errors trigger retry logic if a recovery handler is available.

        Args:
            error: The high-severity error to handle
        """
        # Check if there's a recovery handler for this error code
        recovery_key = f"{error.agent_name}:{error.code}"
        if recovery_key in self._recovery_handlers:
            if error.retry_count < self.max_retry_attempts:
                self.console.print(
                    f"[yellow]Attempting recovery for {error.code}...[/yellow]"
                )
                error.retry_count += 1
                await asyncio.sleep(self.retry_delay)

                try:
                    recovered = await self._recovery_handlers[recovery_key]()
                    if recovered:
                        error.resolved = True
                        self.console.print(
                            f"[green]Recovery successful for {error.code}[/green]"
                        )
                        return
                except Exception as e:
                    self.console.print(
                        f"[red]Recovery failed for {error.code}: {e}[/red]"
                    )

        # No recovery or recovery failed
        self.console.print(
            f"[yellow]High-severity error {error.code} requires attention[/yellow]"
        )

    async def handle_warning(self, error: ErrorRecord) -> None:
        """
        Handle a warning-level error

        Warning-level errors are logged but don't trigger shutdown or retry.
        They represent minor issues that don't impact operations.

        Args:
            error: The warning-level error to handle
        """
        # Just log the error (already displayed)
        pass

    def _display_error(self, error: ErrorRecord) -> None:
        """
        Display an error using Rich for beautiful output

        Args:
            error: The error to display
        """
        # Color mapping by severity
        colors = {
            ErrorSeverity.CRITICAL: "red",
            ErrorSeverity.HIGH: "yellow",
            ErrorSeverity.MEDIUM: "orange",
            ErrorSeverity.LOW: "blue",
            ErrorSeverity.INFO: "dim",
        }

        color = colors.get(error.severity, "white")

        # Create error panel
        error_text = Text()
        error_text.append(f"[{error.agent_name}] ", style=f"bold {color}")
        error_text.append(f"{error.severity.name} ", style=f"bold {color}")
        error_text.append(f"{error.code}\n\n", style=f"bold {color}")
        error_text.append(f"{error.message}", style=color)

        if error.hint:
            error_text.append(f"\n\nHint: {error.hint}", style="dim")

        if error.context:
            context_str = ", ".join(f"{k}={v}" for k, v in error.context.items())
            error_text.append(f"\n\nContext: {context_str}", style="dim")

        panel = Panel(
            error_text,
            title=f"[{color}]Error[/{color}]",
            border_style=color,
            padding=(0, 1),
        )

        self.console.print(panel)

        # Print stack trace if available and severity is HIGH or CRITICAL
        if error.stack_trace and error.severity.value >= ErrorSeverity.HIGH.value:
            self.console.print(f"\n[gray]Stack trace:[/gray]")
            self.console.print(f"[dim]{error.stack_trace}[/dim]\n")

    async def shutdown_engine(self, reason: str) -> None:
        """
        Shutdown the engine gracefully

        This method initiates a graceful shutdown of the entire engine.
        It should be called when a critical error occurs or when manual
        shutdown is requested.

        Args:
            reason: The reason for the shutdown
        """
        if self._is_shutting_down:
            return

        self._is_shutting_down = True

        self.console.print(
            Panel(
                f"[red bold]ENGINE SHUTDOWN INITIATED[/red bold]\n\n"
                f"[yellow]Reason: {reason}[/yellow]\n\n"
                f"[dim]Stopping all agents and cleaning up resources...[/dim]",
                title="[red bold]SHUTDOWN[/red bold]",
                border_style="red",
                padding=(1, 2),
            )
        )

        # Invoke shutdown callback if provided
        if self.shutdown_callback:
            try:
                await self.shutdown_callback(reason)
            except Exception as e:
                self.console.print(
                    f"[red]Error during shutdown callback: {e}[/red]"
                )

    def register_recovery_handler(
        self,
        agent_name: str,
        error_code: str,
        handler: Callable[[], Awaitable[bool]],
    ) -> None:
        """
        Register a recovery handler for a specific error

        Recovery handlers are called when a high-severity error occurs
        and can attempt to recover from the error.

        Args:
            agent_name: Name of the agent
            error_code: Error code to handle
            handler: Async function that returns True if recovery succeeded
        """
        key = f"{agent_name}:{error_code}"
        self._recovery_handlers[key] = handler

    def get_error_stats(self) -> dict[str, Any]:
        """
        Get error statistics

        Returns:
            Dictionary with error statistics including:
            - total_errors: Total number of errors
            - by_severity: Error count by severity
            - by_agent: Error count by agent
            - by_code: Error count by code
            - unresolved: Count of unresolved errors
        """
        by_severity = defaultdict(int)
        by_agent = defaultdict(int)
        by_code = defaultdict(int)
        unresolved = 0

        for error in self._errors:
            by_severity[error.severity.name] += 1
            by_agent[error.agent_name] += 1
            by_code[error.code] += 1
            if not error.resolved:
                unresolved += 1

        total_errors = len(self._errors)

        return {
            "total_errors": total_errors,
            "by_severity": dict(by_severity),
            "by_agent": dict(by_agent),
            "by_code": dict(by_code),
            "unresolved": unresolved,
        }

    def get_recent_errors(
        self, limit: int = 10, severity: ErrorSeverity | None = None
    ) -> list[ErrorRecord]:
        """
        Get recent errors

        Args:
            limit: Maximum number of errors to return
            severity: Filter by severity (if provided)

        Returns:
            List of recent errors
        """
        errors = self._errors.copy()

        # Filter by severity if specified
        if severity:
            errors = [e for e in errors if e.severity == severity]

        # Sort by timestamp (most recent first) and limit
        errors.sort(key=lambda e: e.timestamp, reverse=True)
        return errors[:limit]

    def display_error_stats(self) -> None:
        """Display error statistics in a beautiful table"""
        stats = self.get_error_stats()

        table = Table(title="Error Statistics")
        table.add_column("Category", style="cyan")
        table.add_column("Value", style="magenta")

        table.add_row("Total Errors", str(stats["total_errors"]))
        table.add_row("Unresolved", str(stats["unresolved"]))
        table.add_row("", "")

        for severity, count in stats["by_severity"].items():
            table.add_row(f"Severity: {severity}", str(count))

        table.add_row("", "")

        for agent, count in stats["by_agent"].items():
            table.add_row(f"Agent: {agent}", str(count))

        self.console.print(table)

    def clear_history(self) -> None:
        """Clear error history (useful for testing)"""
        self._errors.clear()
        self._error_counts.clear()

    @property
    def is_shutting_down(self) -> bool:
        """Check if the engine is shutting down"""
        return self._is_shutting_down


# Global error manager instance
_global_error_manager: ErrorManager | None = None


def get_error_manager() -> ErrorManager:
    """Get the global error manager instance"""
    if _global_error_manager is None:
        console = Console()
        _global_error_manager = ErrorManager(console=console)
    return _global_error_manager


def set_error_manager(error_manager: ErrorManager) -> None:
    """Set the global error manager instance"""
    global _global_error_manager
    _global_error_manager = error_manager
