"""
GHOST ENGINE v3.0 - Modern CLI Display System
A beautiful, Rich-powered terminal interface for the 4 Mega-Agent Architecture.

Features:
- Startup banner with agent information
- Step-by-step progress tracking
- Animated spinners for agent work
- Real-time agent status table
- Beautiful error panels
- Live dashboard with layout updates
- Visual log levels with colors and emojis
"""

import os
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, List, Any

from rich.align import Align
from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
)
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

# Initialize Rich Console
console = Console()


# =============================================================================
# AGENT CONFIGURATION
# =============================================================================

class AgentType(Enum):
    """The 4 Mega-Agents of Ghost Engine"""
    SOUL = 1
    SENSES = 2
    BRAIN = 3
    HAND = 4
    GATEWAY = 5


@dataclass
class AgentInfo:
    """Information about each Mega-Agent"""
    id: AgentType
    name: str
    description: str
    emoji: str
    color: str


AGENT_INFO: Dict[AgentType, AgentInfo] = {
    AgentType.SOUL: AgentInfo(
        AgentType.SOUL,
        "SOUL",
        "System, Memory & Evolution",
        "👻",
        "cyan"
    ),
    AgentType.SENSES: AgentInfo(
        AgentType.SENSES,
        "SENSES",
        "Surveillance & Signal Detection",
        "👁️",
        "bright_blue"
    ),
    AgentType.BRAIN: AgentInfo(
        AgentType.BRAIN,
        "BRAIN",
        "Intelligence & Mathematical Verification",
        "🧠",
        "magenta"
    ),
    AgentType.HAND: AgentInfo(
        AgentType.HAND,
        "HAND",
        "Precision Strike & Budget Sentinel",
        "✋",
        "green"
    ),
    AgentType.GATEWAY: AgentInfo(
        AgentType.GATEWAY,
        "GATEWAY",
        "HTTP Interface & External Communication",
        "🌐",
        "yellow"
    ),
}


# =============================================================================
# DISPLAY MANAGER
# =============================================================================

class GhostDisplay:
    """
    Main display manager for Ghost Engine v3.0.
    Coordinates all Rich-based UI components.
    """

    def __init__(self):
        self.console = console
        self.live: Optional[Live] = None
        self.layout: Optional[Layout] = None
        self.agent_status: Dict[AgentType, str] = {
            agent: "IDLE" for agent in AGENT_INFO.keys()
        }
        self.current_cycle = 0
        self.is_windows = os.name == "nt"

    # =========================================================================
    # STARTUP BANNER
    # =========================================================================

    def show_startup_banner(self) -> None:
        """Display the Ghost Engine v3.0 startup banner with 4 Mega-Agents info."""
        banner_text = Text()
        banner_text.append("GHOST ENGINE v3.0", style="bold bright_white on black")
        banner_text.append("\nCodename: Sentient Alpha", style="dim cyan")
        banner_text.append("\n4 Mega-Agent Architecture", style="bold white")

        banner_panel = Panel(
            Align.center(banner_text),
            title="🌟 WELCOME 🌟",
            title_align="center",
            border_style="bright_cyan",
            padding=(1, 2),
        )

        self.console.print()
        self.console.print(Align.center(banner_panel))
        self.console.print()

        # Display the 4 Pillars
        self._show_mega_agents_table()
        self.console.print()

    def _show_mega_agents_table(self) -> None:
        """Display a table showing all 4 Mega-Agents."""
        table = Table(
            title="🏛️  THE 4 PILLARS OF PROFIT 🏛️",
            title_style="bold cyan",
            show_header=True,
            header_style="bold magenta",
            border_style="bright_blue",
            padding=(0, 2),
        )

        table.add_column("Agent", style="bold white", width=12)
        table.add_column("ID", style="dim", width=4)
        table.add_column("Description", style="white", width=35)
        table.add_column("Status", style="dim", width=10)

        for agent_type, info in AGENT_INFO.items():
            if agent_type != AgentType.GATEWAY:  # Show only the 4 main pillars
                table.add_row(
                    f"{info.emoji} {info.name}",
                    str(agent_type.value),
                    info.description,
                    "[dim]INITIALIZING[/dim]"
                )

        self.console.print(Align.center(table))

    # =========================================================================
    # AGENT STATUS TABLE
    # =========================================================================

    def show_agent_status(self) -> None:
        """Display real-time status of all agents."""
        table = Table(
            title="📊 AGENT STATUS 📊",
            title_style="bold cyan",
            show_header=True,
            header_style="bold magenta",
            border_style="bright_blue",
            padding=(0, 1),
        )

        table.add_column("Agent", style="bold white", width=15)
        table.add_column("State", style="white", width=12)
        table.add_column("Last Activity", style="dim", width=25)
        table.add_column("Details", style="white", width=30)

        for agent_type, info in AGENT_INFO.items():
            status = self.agent_status.get(agent_type, "UNKNOWN")
            status_style = self._get_status_style(status)

            table.add_row(
                f"{info.emoji} {info.name}",
                f"[{status_style}]{status}[/{status_style}]",
                datetime.now().strftime("%H:%M:%S"),
                f"Cycle #{self.current_cycle}"
            )

        self.console.print(table)

    def update_agent_status(self, agent: AgentType, status: str) -> None:
        """Update the status of a specific agent."""
        self.agent_status[agent] = status

    def _get_status_style(self, status: str) -> str:
        """Get Rich style based on agent status."""
        status_styles = {
            "IDLE": "dim",
            "ACTIVE": "green",
            "PROCESSING": "yellow",
            "COMPLETE": "bright_green",
            "ERROR": "red",
            "LOCKDOWN": "bold red",
            "THINKING": "cyan",
        }
        return status_styles.get(status, "white")

    # =========================================================================
    # PROGRESS DISPLAY
    # =========================================================================

    @contextmanager
    def cycle_progress(self, cycle_num: int, is_paper_trading: bool = True):
        """
        Display progress bar for a complete trading cycle.

        Args:
            cycle_num: The cycle number
            is_paper_trading: Whether this is paper trading mode
        """
        mode_text = "PAPER TRADING" if is_paper_trading else "LIVE TRADING"
        mode_style = "yellow" if is_paper_trading else "bold red"

        # Create progress tracker
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=40),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=self.console,
            transient=False,
        )

        # Add tasks for each phase
        tasks = {
            "soul": progress.add_task(
                f"[{AGENT_INFO[AgentType.SOUL].color}]👻 SOUL: Authorization & Setup",
                total=100
            ),
            "senses": progress.add_task(
                f"[{AGENT_INFO[AgentType.SENSES].color}]👁️ SENSES: Market Surveillance",
                total=100
            ),
            "brain": progress.add_task(
                f"[{AGENT_INFO[AgentType.BRAIN].color}]🧠 BRAIN: Intelligence Analysis",
                total=100
            ),
            "hand": progress.add_task(
                f"[{AGENT_INFO[AgentType.HAND].color}]✋ HAND: Execution & Trading",
                total=100
            ),
        }

        # Display cycle header
        cycle_header = Panel(
            f"[bold white]Cycle #{cycle_num}[/bold white] - [{mode_style}]{mode_text}[/{mode_style}]",
            title="🚀 TRADING CYCLE 🚀",
            border_style="bright_cyan",
            padding=(0, 2),
        )

        self.console.print()
        self.console.print(cycle_header)
        self.console.print()

        class CycleProgressTracker:
            def __init__(self, progress, tasks):
                self.progress = progress
                self.tasks = tasks

            def update_phase(self, phase: str, advance_to: int = None):
                """Advance progress for a specific phase."""
                if advance_to is not None:
                    self.progress.update(self.tasks[phase], completed=advance_to)
                else:
                    current = self.progress.tasks[self.tasks[phase]].completed
                    self.progress.update(self.tasks[phase], completed=current + 25)

            def complete_phase(self, phase: str):
                """Mark a phase as complete."""
                self.progress.update(self.tasks[phase], completed=100)

        tracker = CycleProgressTracker(progress, tasks)

        try:
            with progress:
                yield tracker
        finally:
            self.console.print()
            success_panel = Panel(
                "[bold green]✓ Cycle Complete[/bold green]",
                border_style="green",
                padding=(0, 2),
            )
            self.console.print(Align.center(success_panel))
            self.console.print()

    # =========================================================================
    # AI THINKING DISPLAY
    # =========================================================================

    @contextmanager
    def agent_thinking(self, agent: AgentType, action: str):
        """
        Display animated spinner while agent is working.

        Args:
            agent: The agent type
            action: Description of what the agent is doing
        """
        info = AGENT_INFO[agent]

        with self.console.status(
            f"[{info.color}]{info.emoji} {info.name}[/]: {action}",
            spinner="dots",
        ) as status:
            try:
                yield status
            finally:
                self.console.print(
                    f"[{info.color}]✓[/] [{info.color}]{info.name}[/]: {action} - Complete",
                    highlight=False
                )

    # =========================================================================
    # ERROR DISPLAY
    # =========================================================================

    def show_error(
        self,
        title: str,
        message: str,
        context: Optional[str] = None,
        hint: Optional[str] = None,
        severity: str = "ERROR",
        agent: Optional[AgentType] = None,
    ) -> None:
        """
        Display a beautiful error panel with context and hints.

        Args:
            title: Error title
            message: Error message
            context: Additional context about the error
            hint: Suggested fix or hint
            severity: Error severity (WARNING, ERROR, CRITICAL)
            agent: The agent that encountered the error
        """
        severity_styles = {
            "WARNING": ("yellow", "⚠️"),
            "ERROR": ("red", "❌"),
            "CRITICAL": ("bold red", "💀"),
        }

        style, emoji = severity_styles.get(severity, ("white", "📋"))

        agent_prefix = ""
        if agent:
            info = AGENT_INFO[agent]
            agent_prefix = f"[{info.color}]{info.emoji} {info.name}[/] - "

        error_content = Group(
            Text(f"{agent_prefix}[{style}]{emoji} {title}[/{style}]", style="bold"),
            Text(),
            Text(message, style="white"),
        )

        if context:
            error_content = Group(
                error_content,
                Text(),
                Text("Context:", style="dim cyan"),
                Text(context, style="dim white"),
            )

        if hint:
            error_content = Group(
                error_content,
                Text(),
                Text("💡 Hint:", style="yellow"),
                Text(hint, style="yellow"),
            )

        error_panel = Panel(
            error_content,
            title=f"[{style}] {severity} [{severity}]",
            border_style=style,
            padding=(1, 2),
        )

        self.console.print()
        self.console.print(error_panel)
        self.console.print()

    # =========================================================================
    # LOG LEVELS
    # =========================================================================

    def log(
        self,
        level: str,
        message: str,
        agent: Optional[AgentType] = None,
    ) -> None:
        """
        Display a log message with visual distinction for different levels.

        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            message: Log message
            agent: The agent generating the log
        """
        level_styles = {
            "DEBUG": ("dim cyan", "🔍"),
            "INFO": ("white", "ℹ️"),
            "WARNING": ("yellow", "⚠️"),
            "ERROR": ("red", "❌"),
            "CRITICAL": ("bold red", "💀"),
            "SUCCESS": ("green", "✅"),
        }

        style, emoji = level_styles.get(level, ("white", "•"))

        agent_prefix = ""
        if agent:
            info = AGENT_INFO[agent]
            agent_prefix = f"[{info.color}]{info.emoji} {info.name}[/] "

        timestamp = datetime.now().strftime("%H:%M:%S")

        self.console.print(
            f"[dim]{timestamp}[/] [{style}]{emoji}[/] {agent_prefix}[{style}]{message}[/{style}]"
        )

    def debug(self, message: str, agent: Optional[AgentType] = None) -> None:
        """Log a debug message."""
        self.log("DEBUG", message, agent)

    def info(self, message: str, agent: Optional[AgentType] = None) -> None:
        """Log an info message."""
        self.log("INFO", message, agent)

    def warning(self, message: str, agent: Optional[AgentType] = None) -> None:
        """Log a warning message."""
        self.log("WARNING", message, agent)

    def error(self, message: str, agent: Optional[AgentType] = None) -> None:
        """Log an error message."""
        self.log("ERROR", message, agent)

    def critical(self, message: str, agent: Optional[AgentType] = None) -> None:
        """Log a critical error message."""
        self.log("CRITICAL", message, agent)

    def success(self, message: str, agent: Optional[AgentType] = None) -> None:
        """Log a success message."""
        self.log("SUCCESS", message, agent)

    # =========================================================================
    # LIVE DASHBOARD
    # =========================================================================

    def start_live_dashboard(self) -> None:
        """Start a live dashboard with real-time updates."""
        self.layout = Layout()

        # Define layout structure
        self.layout.split(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=3),
        )

        self.layout["main"].split_row(
            Layout(name="agents"),
            Layout(name="activity"),
        )

        # Add header
        self.layout["header"].update(
            Panel(
                Align.center(
                    Text("GHOST ENGINE v3.0 - LIVE DASHBOARD", style="bold bright_cyan")
                ),
                style="bright_black",
            )
        )

        # Add agent status table
        self.layout["agents"].update(self._create_agent_status_panel())

        # Add activity feed
        self.layout["activity"].update(
            Panel(
                Text("Activity feed coming soon...", style="dim"),
                title="📋 ACTIVITY",
                border_style="bright_blue",
            )
        )

        # Add footer
        self.layout["footer"].update(
            Panel(
                Align.center(
                    Text("Press Ctrl+C to exit", style="dim white")
                ),
                style="bright_black",
            )
        )

        # Start live display
        self.live = Live(
            self.layout,
            console=self.console,
            refresh_per_second=4,
        )
        self.live.start()

    def update_dashboard(self) -> None:
        """Update the live dashboard with current status."""
        if self.live and self.layout:
            self.layout["agents"].update(self._create_agent_status_panel())

    def _create_agent_status_panel(self) -> Panel:
        """Create the agent status panel for the dashboard."""
        table = Table(
            show_header=False,
            box=None,
            padding=(0, 1),
        )

        table.add_column("Agent", style="bold white")
        table.add_column("Status")

        for agent_type, info in AGENT_INFO.items():
            status = self.agent_status.get(agent_type, "UNKNOWN")
            status_style = self._get_status_style(status)

            table.add_row(
                f"{info.emoji} {info.name}",
                f"[{status_style}]●[/] {status}",
            )

        return Panel(
            table,
            title="👥 AGENTS",
            border_style="bright_blue",
        )

    def stop_live_dashboard(self) -> None:
        """Stop the live dashboard."""
        if self.live:
            self.live.stop()
            self.live = None

    # =========================================================================
    # SYSTEM MESSAGES
    # =========================================================================

    def show_system_online(self) -> None:
        """Display system online message."""
        panel = Panel(
            Align.center(
                Text("✅ ALL SYSTEMS OPERATIONAL", style="bold green on black")
            ),
            border_style="green",
            padding=(1, 3),
        )
        self.console.print()
        self.console.print(Align.center(panel))
        self.console.print()

    def show_shutdown_message(self) -> None:
        """Display shutdown message."""
        panel = Panel(
            Align.center(
                Group(
                    Text("👻 GHOST ENGINE SHUTDOWN", style="bold red"),
                    Text(),
                    Text("The 4 Pillars are now resting.", style="dim white"),
                )
            ),
            border_style="red",
            padding=(1, 3),
        )
        self.console.print()
        self.console.print(Align.center(panel))
        self.console.print()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

# Global display instance
_display: Optional[GhostDisplay] = None


def get_display() -> GhostDisplay:
    """Get the global GhostDisplay instance."""
    global _display
    if _display is None:
        _display = GhostDisplay()
    return _display


def show_startup_banner() -> None:
    """Show the startup banner."""
    get_display().show_startup_banner()


def show_agent_status() -> None:
    """Show the agent status table."""
    get_display().show_agent_status()


def update_agent_status(agent: AgentType, status: str) -> None:
    """Update agent status."""
    get_display().update_agent_status(agent, status)


def log_debug(message: str, agent: Optional[AgentType] = None) -> None:
    """Log a debug message."""
    get_display().debug(message, agent)


def log_info(message: str, agent: Optional[AgentType] = None) -> None:
    """Log an info message."""
    get_display().info(message, agent)


def log_warning(message: str, agent: Optional[AgentType] = None) -> None:
    """Log a warning message."""
    get_display().warning(message, agent)


def log_error(message: str, agent: Optional[AgentType] = None) -> None:
    """Log an error message."""
    get_display().error(message, agent)


def log_critical(message: str, agent: Optional[AgentType] = None) -> None:
    """Log a critical message."""
    get_display().critical(message, agent)


def log_success(message: str, agent: Optional[AgentType] = None) -> None:
    """Log a success message."""
    get_display().success(message, agent)


def show_error(
    title: str,
    message: str,
    context: Optional[str] = None,
    hint: Optional[str] = None,
    severity: str = "ERROR",
    agent: Optional[AgentType] = None,
) -> None:
    """Show an error panel."""
    get_display().show_error(title, message, context, hint, severity, agent)


# Export main class and convenience functions
__all__ = [
    "GhostDisplay",
    "AgentType",
    "get_display",
    "show_startup_banner",
    "show_agent_status",
    "update_agent_status",
    "log_debug",
    "log_info",
    "log_warning",
    "log_error",
    "log_critical",
    "log_success",
    "show_error",
]
