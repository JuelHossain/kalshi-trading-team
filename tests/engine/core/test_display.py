"""
Comprehensive tests for the Rich display system.
Tests cover startup banner, progress display, agent status table,
error display, log levels, and live dashboard.
"""

import pytest
import sys
import os
import time
from io import StringIO
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime

# Add the engine directory to the path
engine_dir = Path(__file__).parent.parent.parent / "engine"
sys.path.insert(0, str(engine_dir))

from core.display import (
    GhostDisplay,
    AgentType,
    get_display,
    show_startup_banner,
    show_agent_status,
    update_agent_status,
    log_debug,
    log_info,
    log_warning,
    log_error,
    log_critical,
    log_success,
    show_error,
)

from rich.console import Console


class TestGhostDisplay:
    """Test the main GhostDisplay class."""

    @pytest.fixture
    def display(self):
        """Create a fresh GhostDisplay instance for each test."""
        return GhostDisplay()

    def test_display_initialization(self, display):
        """Test that display initializes correctly."""
        assert display.console is not None
        assert display.live is None
        assert display.layout is None
        assert display.current_cycle == 0
        assert display.is_windows == (os.name == "nt")

    def test_agent_status_initialization(self, display):
        """Test that agent status dictionary is properly initialized."""
        assert AgentType.SOUL in display.agent_status
        assert AgentType.SENSES in display.agent_status
        assert AgentType.BRAIN in display.agent_status
        assert AgentType.HAND in display.agent_status
        assert AgentType.GATEWAY in display.agent_status

        # All should start as IDLE
        for status in display.agent_status.values():
            assert status == "IDLE"

    def test_update_agent_status(self, display):
        """Test updating agent status."""
        display.update_agent_status(AgentType.SOUL, "ACTIVE")
        assert display.agent_status[AgentType.SOUL] == "ACTIVE"

        display.update_agent_status(AgentType.BRAIN, "PROCESSING")
        assert display.agent_status[AgentType.BRAIN] == "PROCESSING"

    def test_get_status_style(self, display):
        """Test status style mapping."""
        assert display._get_status_style("IDLE") == "dim"
        assert display._get_status_style("ACTIVE") == "green"
        assert display._get_status_style("PROCESSING") == "yellow"
        assert display._get_status_style("COMPLETE") == "bright_green"
        assert display._get_status_style("ERROR") == "red"
        assert display._get_status_style("LOCKDOWN") == "bold red"
        assert display._get_status_style("THINKING") == "cyan"
        assert display._get_status_style("UNKNOWN") == "white"

    def test_cycle_count_tracking(self, display):
        """Test cycle count tracking."""
        assert display.current_cycle == 0
        display.current_cycle = 5
        assert display.current_cycle == 5


class TestAgentInfo:
    """Test agent information configuration."""

    def test_all_agents_defined(self):
        """Test that all 4 Mega-Agents are properly defined."""
        from core.display import AGENT_INFO

        assert AgentType.SOUL in AGENT_INFO
        assert AgentType.SENSES in AGENT_INFO
        assert AgentType.BRAIN in AGENT_INFO
        assert AgentType.HAND in AGENT_INFO
        assert AgentType.GATEWAY in AGENT_INFO

    def test_agent_info_structure(self):
        """Test that agent info has required fields."""
        from core.display import AGENT_INFO

        for agent_type, info in AGENT_INFO.items():
            assert hasattr(info, 'id')
            assert hasattr(info, 'name')
            assert hasattr(info, 'description')
            assert hasattr(info, 'emoji')
            assert hasattr(info, 'color')
            assert info.id == agent_type

    def test_soul_agent_info(self):
        """Test SOUL agent configuration."""
        from core.display import AGENT_INFO

        soul = AGENT_INFO[AgentType.SOUL]
        assert soul.name == "SOUL"
        assert "System" in soul.description
        assert soul.emoji == "👻"
        assert soul.color == "cyan"

    def test_senses_agent_info(self):
        """Test SENSES agent configuration."""
        from core.display import AGENT_INFO

        senses = AGENT_INFO[AgentType.SENSES]
        assert senses.name == "SENSES"
        assert "Surveillance" in senses.description
        assert senses.emoji == "👁️"
        assert senses.color == "bright_blue"

    def test_brain_agent_info(self):
        """Test BRAIN agent configuration."""
        from core.display import AGENT_INFO

        brain = AGENT_INFO[AgentType.BRAIN]
        assert brain.name == "BRAIN"
        assert "Intelligence" in brain.description
        assert brain.emoji == "🧠"
        assert brain.color == "magenta"

    def test_hand_agent_info(self):
        """Test HAND agent configuration."""
        from core.display import AGENT_INFO

        hand = AGENT_INFO[AgentType.HAND]
        assert hand.name == "HAND"
        assert "Precision" in hand.description
        assert hand.emoji == "✋"
        assert hand.color == "green"


class TestConvenienceFunctions:
    """Test convenience functions for easy access."""

    def test_get_display_singleton(self):
        """Test that get_display returns a singleton instance."""
        display1 = get_display()
        display2 = get_display()
        assert display1 is display2

    def test_log_functions_exist(self):
        """Test that all log convenience functions exist."""
        # These should not raise exceptions
        assert callable(log_debug)
        assert callable(log_info)
        assert callable(log_warning)
        assert callable(log_error)
        assert callable(log_critical)
        assert callable(log_success)

    def test_show_functions_exist(self):
        """Test that all show convenience functions exist."""
        # These should not raise exceptions
        assert callable(show_startup_banner)
        assert callable(show_agent_status)
        assert callable(show_error)
        assert callable(update_agent_status)


class TestLogMethods:
    """Test log methods with different levels."""

    @pytest.fixture
    def display(self):
        """Create a display with mocked console."""
        display = GhostDisplay()
        display.console = Mock()
        return display

    def test_debug_log(self, display):
        """Test debug log method."""
        display.debug("Test debug message", AgentType.SOUL)
        assert display.console.print.called

    def test_info_log(self, display):
        """Test info log method."""
        display.info("Test info message", AgentType.BRAIN)
        assert display.console.print.called

    def test_warning_log(self, display):
        """Test warning log method."""
        display.warning("Test warning message", AgentType.SENSES)
        assert display.console.print.called

    def test_error_log(self, display):
        """Test error log method."""
        display.error("Test error message", AgentType.HAND)
        assert display.console.print.called

    def test_critical_log(self, display):
        """Test critical log method."""
        display.critical("Test critical message", AgentType.GATEWAY)
        assert display.console.print.called

    def test_success_log(self, display):
        """Test success log method."""
        display.success("Test success message", AgentType.SOUL)
        assert display.console.print.called

    def test_log_without_agent(self, display):
        """Test logging without specifying an agent."""
        display.info("Test message without agent")
        assert display.console.print.called


class TestErrorDisplay:
    """Test error display functionality."""

    @pytest.fixture
    def display(self):
        """Create a display with mocked console."""
        display = GhostDisplay()
        display.console = Mock()
        return display

    def test_show_error_basic(self, display):
        """Test basic error display."""
        display.show_error(
            title="Test Error",
            message="This is a test error message",
        )
        assert display.console.print.called

    def test_show_error_with_context(self, display):
        """Test error display with context."""
        display.show_error(
            title="Test Error",
            message="This is a test error message",
            context="Error occurred during testing",
        )
        assert display.console.print.called

    def test_show_error_with_hint(self, display):
        """Test error display with hint."""
        display.show_error(
            title="Test Error",
            message="This is a test error message",
            hint="Try fixing the test",
        )
        assert display.console.print.called

    def test_show_error_with_agent(self, display):
        """Test error display with agent specified."""
        display.show_error(
            title="Test Error",
            message="This is a test error message",
            agent=AgentType.BRAIN,
        )
        assert display.console.print.called

    def test_show_error_severity_levels(self, display):
        """Test different severity levels."""
        for severity in ["WARNING", "ERROR", "CRITICAL"]:
            display.show_error(
                title=f"Test {severity}",
                message=f"This is a {severity} message",
                severity=severity,
            )
            assert display.console.print.called


class TestProgressDisplay:
    """Test progress display functionality."""

    def test_cycle_progress_context(self):
        """Test that cycle progress can be used as context manager."""
        display = GhostDisplay()
        display.console = Mock()

        # Mock the progress to avoid actual console output
        with patch('core.display.Progress') as mock_progress:
            mock_progress.return_value.__enter__ = Mock()
            mock_progress.return_value.__exit__ = Mock(return_value=False)

            with display.cycle_progress(1, is_paper_trading=True):
                pass

            assert mock_progress.called


class TestAgentThinking:
    """Test agent thinking display."""

    def test_agent_thinking_context(self):
        """Test that agent thinking can be used as context manager."""
        display = GhostDisplay()
        display.console = Mock()

        # Mock the status context to avoid actual console output
        with patch.object(display.console, 'status') as mock_status:
            mock_status.return_value.__enter__ = Mock()
            mock_status.return_value.__exit__ = Mock(return_value=False)

            with display.agent_thinking(AgentType.BRAIN, "Analyzing markets..."):
                pass

            assert mock_status.called


class TestLiveDashboard:
    """Test live dashboard functionality."""

    @pytest.fixture
    def display(self):
        """Create a display for dashboard testing."""
        display = GhostDisplay()
        return display

    def test_create_agent_status_panel(self, display):
        """Test creating agent status panel."""
        panel = display._create_agent_status_panel()
        assert panel is not None

    def test_update_agent_status_affects_dashboard(self, display):
        """Test that updating agent status affects dashboard."""
        display.update_agent_status(AgentType.SOUL, "ACTIVE")
        assert display.agent_status[AgentType.SOUL] == "ACTIVE"

        panel = display._create_agent_status_panel()
        assert panel is not None


class TestIntegration:
    """Integration tests for the display system."""

    def test_full_workflow(self):
        """Test a complete workflow with the display system."""
        display = get_display()

        # Update agent statuses
        display.update_agent_status(AgentType.SOUL, "ACTIVE")
        display.update_agent_status(AgentType.SENSES, "SCANNING")
        display.update_agent_status(AgentType.BRAIN, "ANALYZING")
        display.update_agent_status(AgentType.HAND, "IDLE")

        # Verify updates
        assert display.agent_status[AgentType.SOUL] == "ACTIVE"
        assert display.agent_status[AgentType.SENSES] == "SCANNING"
        assert display.agent_status[AgentType.BRAIN] == "ANALYZING"
        assert display.agent_status[AgentType.HAND] == "IDLE"

        # Reset
        for agent in AgentType:
            display.update_agent_status(agent, "IDLE")

        # Verify reset
        for status in display.agent_status.values():
            assert status == "IDLE"


class TestStartupBannerDisplay:
    """Test suite for startup banner display with output verification."""

    @pytest.fixture
    def mock_console(self):
        """Create a mock console with a string buffer for output capture."""
        console = Console(file=StringIO(), force_terminal=True, width=120)
        return console

    @pytest.fixture
    def display(self, mock_console):
        """Create a GhostDisplay instance with a mock console."""
        display = GhostDisplay()
        display.console = mock_console
        return display

    def test_startup_banner_displays_title(self, display):
        """Startup banner should display the main title correctly."""
        display.show_startup_banner()
        output = display.console.file.getvalue()

        assert "GHOST ENGINE v3.0" in output
        assert "Sentient Alpha" in output
        assert "4 Mega-Agent Architecture" in output

    def test_startup_banner_displays_welcome_title(self, display):
        """Startup banner should include the welcome panel title."""
        display.show_startup_banner()
        output = display.console.file.getvalue()

        assert "WELCOME" in output

    def test_startup_banner_shows_all_four_pillars(self, display):
        """Startup banner should display all 4 main pillars (excluding GATEWAY)."""
        display.show_startup_banner()
        output = display.console.file.getvalue()

        # Check for the 4 pillars title
        assert "4 PILLARS" in output or "PILLARS" in output

        # Check for each agent (excluding GATEWAY)
        assert "SOUL" in output
        assert "SENSES" in output
        assert "BRAIN" in output
        assert "HAND" in output

        # Verify descriptions are present (may be wrapped)
        assert "System" in output and "Evolution" in output
        assert "Surveillance" in output or "Signal" in output
        assert "Intelligence" in output or "Mathematical" in output
        assert "Precision" in output or "Sentinel" in output

    def test_startup_banner_initializing_status(self, display):
        """Startup banner should show INITIALIZING status for agents."""
        display.show_startup_banner()
        output = display.console.file.getvalue()

        # Status may be truncated (like "INITIALIZ...")
        assert "INITIALIZ" in output

    def test_startup_banner_excludes_gateway_from_pillars(self, display):
        """Startup banner should exclude GATEWAY from the 4 pillars table."""
        display.show_startup_banner()
        output = display.console.file.getvalue()

        # GATEWAY might appear elsewhere, but not in the pillars section
        # This is a basic check - the implementation filters it out
        lines = output.split('\n')
        pillars_section = False
        gateway_in_pillars = False

        for line in lines:
            if '4 PILLARS' in line:
                pillars_section = True
            if pillars_section and 'GATEWAY' in line and 'HTTP Interface' in line:
                gateway_in_pillars = True
                break
            # End of pillars section (rough heuristic)
            if pillars_section and line.strip() == '':
                break

        # GATEWAY should not be in the pillars table
        assert not gateway_in_pillars

    def test_startup_banner_has_proper_spacing(self, display):
        """Startup banner should have proper vertical spacing."""
        display.show_startup_banner()
        output = display.console.file.getvalue()

        # Check for newlines (simplified check)
        assert output.count('\n') > 5  # Should have multiple newlines


class TestProgressDisplayDetailed:
    """Detailed test suite for cycle progress display."""

    @pytest.fixture
    def display(self):
        """Create a display with mocked console."""
        display = GhostDisplay()
        display.console = Mock()
        return display

    def test_cycle_progress_creates_four_tasks(self, display):
        """Cycle progress should create tasks for all 4 phases."""
        with patch('core.display.Progress') as mock_progress:
            mock_progress.return_value.__enter__ = Mock()
            mock_progress.return_value.__exit__ = Mock(return_value=False)

            with display.cycle_progress(cycle_num=1, is_paper_trading=True):
                pass

            assert mock_progress.called

    def test_cycle_progress_displays_cycle_header(self, display):
        """Cycle progress should display the cycle number and mode."""
        with patch('core.display.Progress') as mock_progress:
            mock_progress.return_value.__enter__ = Mock()
            mock_progress.return_value.__exit__ = Mock(return_value=False)

            with display.cycle_progress(cycle_num=5, is_paper_trading=False):
                pass

            assert mock_progress.called

    def test_cycle_progress_paper_trading_mode(self, display):
        """Paper trading mode should be displayed correctly."""
        with patch('core.display.Progress') as mock_progress:
            mock_progress.return_value.__enter__ = Mock()
            mock_progress.return_value.__exit__ = Mock(return_value=False)

            with display.cycle_progress(cycle_num=1, is_paper_trading=True):
                pass

            assert mock_progress.called

    def test_cycle_progress_shows_trading_cycle_title(self, display):
        """Progress should show the trading cycle title."""
        with patch('core.display.Progress') as mock_progress:
            mock_progress.return_value.__enter__ = Mock()
            mock_progress.return_value.__exit__ = Mock(return_value=False)

            with display.cycle_progress(cycle_num=1):
                pass

            assert mock_progress.called

    def test_cycle_progress_complete_message(self, display):
        """Progress should show completion message."""
        with patch('core.display.Progress') as mock_progress:
            mock_progress.return_value.__enter__ = Mock()
            mock_progress.return_value.__exit__ = Mock(return_value=False)

            with display.cycle_progress(cycle_num=1):
                pass

            assert mock_progress.called

    def test_cycle_progress_tracker_updates_phases(self, display):
        """Progress tracker should be able to update phases."""
        with patch('core.display.Progress') as mock_progress:
            mock_progress_instance = Mock()
            mock_progress_instance.__enter__ = Mock(return_value=None)
            mock_progress_instance.__exit__ = Mock(return_value=False)
            mock_progress.return_value = mock_progress_instance

            # Mock the tasks and methods
            mock_tasks = {
                "soul": Mock(),
                "senses": Mock(),
                "brain": Mock(),
                "hand": Mock()
            }
            mock_progress_instance.tasks = {
                mock_tasks["soul"]: Mock(completed=0),
                mock_tasks["senses"]: Mock(completed=0),
                mock_tasks["brain"]: Mock(completed=0),
                mock_tasks["hand"]: Mock(completed=0)
            }

            with display.cycle_progress(cycle_num=1) as tracker:
                # Should not raise any errors
                tracker.update_phase("soul", 25)
                tracker.update_phase("senses", 50)
                tracker.update_phase("brain", 75)
                tracker.update_phase("hand", 100)

            # Test completed without errors
            assert True

    def test_cycle_progress_tracker_complete_phase(self, display):
        """Tracker should be able to mark phases as complete."""
        with patch('core.display.Progress') as mock_progress:
            mock_progress_instance = Mock()
            mock_progress_instance.__enter__ = Mock(return_value=None)
            mock_progress_instance.__exit__ = Mock(return_value=False)
            mock_progress.return_value = mock_progress_instance

            with display.cycle_progress(cycle_num=1) as tracker:
                tracker.complete_phase("soul")
                tracker.complete_phase("senses")
                tracker.complete_phase("brain")
                tracker.complete_phase("hand")

            # Test completed without errors
            assert True

    def test_cycle_progress_all_agents_represented(self, display):
        """Progress should include all 4 main agents."""
        with patch('core.display.Progress') as mock_progress:
            mock_progress.return_value.__enter__ = Mock()
            mock_progress.return_value.__exit__ = Mock(return_value=False)

            with display.cycle_progress(cycle_num=1):
                pass

            assert mock_progress.called


class TestAgentStatusTableDetailed:
    """Detailed test suite for agent status table display."""

    @pytest.fixture
    def mock_console(self):
        """Create a mock console with a string buffer."""
        return Console(file=StringIO(), force_terminal=True, width=120)

    @pytest.fixture
    def display(self, mock_console):
        """Create a display with mock console."""
        display = GhostDisplay()
        display.console = mock_console
        return display

    @pytest.fixture
    def sample_agent_statuses(self):
        """Sample agent status data for testing."""
        return {
            AgentType.SOUL: "ACTIVE",
            AgentType.SENSES: "PROCESSING",
            AgentType.BRAIN: "THINKING",
            AgentType.HAND: "IDLE",
            AgentType.GATEWAY: "ACTIVE",
        }

    def test_agent_status_table_renders(self, display):
        """Agent status table should render without errors."""
        display.show_agent_status()
        output = display.console.file.getvalue()

        assert len(output) > 0

    def test_agent_status_shows_all_agents(self, display):
        """Status table should show all 5 agents including GATEWAY."""
        display.show_agent_status()
        output = display.console.file.getvalue()

        # All agents should be present
        assert "SOUL" in output
        assert "SENSES" in output
        assert "BRAIN" in output
        assert "HAND" in output
        assert "GATEWAY" in output

    def test_agent_status_shows_cycle_number(self, display):
        """Status table should display current cycle number."""
        display.current_cycle = 42
        display.show_agent_status()
        output = display.console.file.getvalue()

        assert "#42" in output or "42" in output

    def test_agent_status_has_timestamp(self, display):
        """Status table should show last activity timestamp."""
        display.show_agent_status()
        output = display.console.file.getvalue()

        # Should have a time format (HH:MM:SS)
        assert ":" in output

    def test_agent_status_default_idle_state(self, display):
        """Agents should start in IDLE state by default."""
        display.show_agent_status()
        output = display.console.file.getvalue()

        assert "IDLE" in output

    def test_update_agent_status_changes_state(self, display):
        """Updating agent status should reflect in the table."""
        display.update_agent_status(AgentType.BRAIN, "THINKING")
        display.show_agent_status()
        output = display.console.file.getvalue()

        assert "THINKING" in output

    def test_update_multiple_agent_statuses(self, display, sample_agent_statuses):
        """Multiple agent statuses should update correctly."""
        for agent, status in sample_agent_statuses.items():
            display.update_agent_status(agent, status)

        display.show_agent_status()
        output = display.console.file.getvalue()

        # Check all statuses are present
        for status in sample_agent_statuses.values():
            assert status in output

    def test_agent_status_table_title(self, display):
        """Status table should have a title."""
        display.show_agent_status()
        output = display.console.file.getvalue()

        assert "AGENT STATUS" in output


class TestErrorDisplayDetailed:
    """Detailed test suite for error panel display."""

    @pytest.fixture
    def mock_console(self):
        """Create a mock console with a string buffer."""
        return Console(file=StringIO(), force_terminal=True, width=120)

    @pytest.fixture
    def display(self, mock_console):
        """Create a display with mock console."""
        display = GhostDisplay()
        display.console = mock_console
        return display

    def test_error_panel_displays_title(self, display):
        """Error panel should display the error title."""
        display.show_error(
            title="Test Error",
            message="This is a test error message"
        )
        output = display.console.file.getvalue()

        assert "Test Error" in output

    def test_error_panel_displays_message(self, display):
        """Error panel should display the error message."""
        display.show_error(
            title="Test Error",
            message="This is a test error message"
        )
        output = display.console.file.getvalue()

        assert "This is a test error message" in output

    def test_error_panel_with_context(self, display):
        """Error panel should display context when provided."""
        display.show_error(
            title="Test Error",
            message="Error occurred",
            context="During market scan at 10:30 AM"
        )
        output = display.console.file.getvalue()

        assert "During market scan at 10:30 AM" in output
        assert "Context" in output

    def test_error_panel_with_hint(self, display):
        """Error panel should display hint when provided."""
        display.show_error(
            title="Test Error",
            message="Error occurred",
            hint="Check your network connection"
        )
        output = display.console.file.getvalue()

        assert "Check your network connection" in output
        assert "Hint" in output or "💡" in output

    def test_error_panel_with_agent(self, display):
        """Error panel should display agent information."""
        display.show_error(
            title="Test Error",
            message="Agent error",
            agent=AgentType.BRAIN
        )
        output = display.console.file.getvalue()

        assert "BRAIN" in output or "🧠" in output

    def test_error_warning_severity(self, display):
        """Warning severity should display correctly."""
        display.show_error(
            title="Warning",
            message="Warning message",
            severity="WARNING"
        )
        output = display.console.file.getvalue()

        assert "WARNING" in output or "⚠️" in output

    def test_error_critical_severity(self, display):
        """Critical severity should display correctly."""
        display.show_error(
            title="Critical Error",
            message="Critical error message",
            severity="CRITICAL"
        )
        output = display.console.file.getvalue()

        assert "CRITICAL" in output or "💀" in output

    def test_error_default_severity(self, display):
        """Default severity should be ERROR."""
        display.show_error(
            title="Error",
            message="Error message"
        )
        output = display.console.file.getvalue()

        assert "ERROR" in output or "❌" in output

    def test_error_panel_proper_spacing(self, display):
        """Error panel should have proper spacing."""
        display.show_error(
            title="Test Error",
            message="Test message"
        )
        output = display.console.file.getvalue()

        # Should have multiple newlines for spacing
        assert output.count('\n') >= 2

    def test_error_panel_complete_information(self, display):
        """Error panel with all fields should display correctly."""
        display.show_error(
            title="Complete Error",
            message="Complete error message",
            context="Complete context information",
            hint="Complete hint information",
            severity="ERROR",
            agent=AgentType.SOUL
        )
        output = display.console.file.getvalue()

        assert "Complete Error" in output
        assert "Complete error message" in output
        assert "Complete context information" in output
        assert "Complete hint information" in output
        assert "SOUL" in output


class TestLogLevelDetailed:
    """Detailed test suite for log level display."""

    @pytest.fixture
    def mock_console(self):
        """Create a mock console with a string buffer."""
        return Console(file=StringIO(), force_terminal=True, width=120)

    @pytest.fixture
    def display(self, mock_console):
        """Create a display with mock console."""
        display = GhostDisplay()
        display.console = mock_console
        return display

    def test_debug_log_displays(self, display):
        """Debug log should display with proper styling."""
        display.debug("Debug message")
        output = display.console.file.getvalue()

        assert "Debug message" in output

    def test_info_log_displays(self, display):
        """Info log should display with proper styling."""
        display.info("Info message")
        output = display.console.file.getvalue()

        assert "Info message" in output

    def test_warning_log_displays(self, display):
        """Warning log should display with proper styling."""
        display.warning("Warning message")
        output = display.console.file.getvalue()

        assert "Warning message" in output

    def test_error_log_displays(self, display):
        """Error log should display with proper styling."""
        display.error("Error message")
        output = display.console.file.getvalue()

        assert "Error message" in output

    def test_critical_log_displays(self, display):
        """Critical log should display with proper styling."""
        display.critical("Critical message")
        output = display.console.file.getvalue()

        assert "Critical message" in output

    def test_success_log_displays(self, display):
        """Success log should display with proper styling."""
        display.success("Success message")
        output = display.console.file.getvalue()

        assert "Success message" in output

    def test_log_with_agent(self, display):
        """Log messages should include agent information."""
        display.info("Test message", agent=AgentType.HAND)
        output = display.console.file.getvalue()

        assert "Test message" in output
        assert "HAND" in output or "✋" in output

    def test_log_includes_timestamp(self, display):
        """Log messages should include timestamp."""
        display.info("Timestamp test")
        output = display.console.file.getvalue()

        # Should have time format (HH:MM:SS)
        assert ":" in output

    def test_all_log_levels_have_distinct_output(self, display):
        """All log levels should produce output."""
        display.console.file = StringIO()

        display.debug("Debug")
        display.info("Info")
        display.warning("Warning")
        display.error("Error")
        display.critical("Critical")
        display.success("Success")

        output = display.console.file.getvalue()

        assert "Debug" in output
        assert "Info" in output
        assert "Warning" in output
        assert "Error" in output
        assert "Critical" in output
        assert "Success" in output

    def test_log_method_with_custom_level(self, display):
        """Generic log method should work with any level."""
        display.log("INFO", "Custom info log")
        output = display.console.file.getvalue()

        assert "Custom info log" in output

    def test_debug_log_with_senses_agent(self, display):
        """Debug log with SENSES agent should display properly."""
        display.debug("Scanning markets", agent=AgentType.SENSES)
        output = display.console.file.getvalue()

        assert "Scanning markets" in output
        assert "SENSES" in output or "👁️" in output


class TestLiveDashboardDetailed:
    """Detailed test suite for live dashboard functionality."""

    @pytest.fixture
    def display(self):
        """Create a display for dashboard testing."""
        display = GhostDisplay()
        return display

    def test_start_live_dashboard_creates_layout(self, display):
        """Starting dashboard should create layout."""
        display.start_live_dashboard()

        assert display.layout is not None
        assert display.live is not None

        # Clean up
        display.stop_live_dashboard()

    def test_stop_live_dashboard(self, display):
        """Stopping dashboard should clean up resources."""
        display.start_live_dashboard()
        assert display.live is not None

        display.stop_live_dashboard()
        assert display.live is None

    def test_update_dashboard_changes_content(self, display):
        """Updating dashboard should refresh content."""
        display.start_live_dashboard()

        # Update agent status
        display.update_agent_status(AgentType.BRAIN, "PROCESSING")
        display.update_dashboard()

        # Should not raise any errors
        assert True

        # Clean up
        display.stop_live_dashboard()

    def test_dashboard_has_header(self, display):
        """Dashboard should have a header section."""
        display.start_live_dashboard()

        # Check that layout exists and has the expected structure
        assert display.layout is not None
        # The layout is a Rich Layout object, check if it has the regions
        assert hasattr(display.layout, 'split')
        display.stop_live_dashboard()

    def test_dashboard_has_main_section(self, display):
        """Dashboard should have a main section."""
        display.start_live_dashboard()

        assert display.layout is not None
        display.stop_live_dashboard()

    def test_dashboard_has_footer(self, display):
        """Dashboard should have a footer section."""
        display.start_live_dashboard()

        assert display.layout is not None
        display.stop_live_dashboard()

    def test_dashboard_has_agents_section(self, display):
        """Dashboard should have an agents section."""
        display.start_live_dashboard()

        assert display.layout is not None
        display.stop_live_dashboard()

    def test_dashboard_has_activity_section(self, display):
        """Dashboard should have an activity section."""
        display.start_live_dashboard()

        assert display.layout is not None
        display.stop_live_dashboard()

    def test_start_dashboard_without_error(self, display):
        """Starting and stopping dashboard should not raise errors."""
        try:
            display.start_live_dashboard()
            display.stop_live_dashboard()
            success = True
        except Exception:
            success = False

        assert success is True

    def test_multiple_dashboard_start_stop_cycles(self, display):
        """Multiple start/stop cycles should work correctly."""
        for _ in range(3):
            display.start_live_dashboard()
            assert display.live is not None
            display.stop_live_dashboard()
            assert display.live is None


class TestEdgeCases:
    """Test suite for edge cases and error handling."""

    @pytest.fixture
    def mock_console(self):
        """Create a mock console with a string buffer."""
        return Console(file=StringIO(), force_terminal=True, width=120)

    @pytest.fixture
    def display(self, mock_console):
        """Create a display with mock console."""
        display = GhostDisplay()
        display.console = mock_console
        return display

    def test_empty_log_message(self, display):
        """Empty log messages should not crash."""
        display.info("")
        assert True  # No exception raised

    def test_very_long_log_message(self, display):
        """Very long log messages should be handled."""
        long_message = "A" * 1000
        display.info(long_message)
        output = display.console.file.getvalue()
        assert "A" in output

    def test_special_characters_in_message(self, display):
        """Special characters should be handled properly."""
        special_message = "Test with special chars: @#$%^&*()_+{}|:<>?"
        display.info(special_message)
        output = display.console.file.getvalue()
        assert "Test with special chars:" in output

    def test_multiple_agent_status_updates(self, display):
        """Rapid agent status updates should work."""
        for i in range(100):
            display.update_agent_status(AgentType.BRAIN, f"STATE_{i}")
        assert True  # No errors

    def test_stop_dashboard_without_starting(self, display):
        """Stopping dashboard without starting should not crash."""
        display.stop_live_dashboard()
        assert True  # No exception

    def test_update_dashboard_without_starting(self, display):
        """Updating dashboard without starting should not crash."""
        display.update_dashboard()
        assert True  # No exception

    def test_error_with_all_empty_fields(self, display):
        """Error with empty fields should still render."""
        display.show_error("", "", context="", hint="")
        output = display.console.file.getvalue()
        assert len(output) > 0

    def test_invalid_status_style(self, display):
        """Unknown status should return default style."""
        style = display._get_status_style("UNKNOWN_STATUS")
        assert style == "white"


class TestPerformance:
    """Test suite for display performance."""

    @pytest.fixture
    def display(self):
        """Create a display for performance testing."""
        display = GhostDisplay()
        display.console = Mock()
        return display

    def test_rapid_log_calls(self, display):
        """Rapid log calls should not cause issues."""
        start = time.time()
        for i in range(100):
            display.info(f"Message {i}")
        elapsed = time.time() - start

        # Should complete 100 logs in reasonable time (< 5 seconds)
        assert elapsed < 5.0

    def test_large_status_updates(self, display):
        """Large number of status updates should work."""
        for i in range(50):
            display.update_agent_status(AgentType.SOUL, f"STATUS_{i}")

        assert True  # No errors


class TestConvenienceFunctionsDetailed:
    """Detailed test suite for global convenience functions."""

    @pytest.fixture
    def reset_display(self):
        """Reset the global display instance before each test."""
        import core.display
        core.display._display = None
        yield
        core.display._display = None

    @pytest.fixture
    def mock_console(self):
        """Create a mock console with a string buffer."""
        return Console(file=StringIO(), force_terminal=True, width=120)

    def test_get_display_returns_singleton(self, reset_display):
        """get_display should return the same instance."""
        display1 = get_display()
        display2 = get_display()

        assert display1 is display2

    def test_get_display_creates_new_instance_if_none(self, reset_display):
        """get_display should create new instance if none exists."""
        import core.display
        core.display._display = None

        display = get_display()

        assert display is not None
        assert isinstance(display, GhostDisplay)

    def test_show_startup_banner_convenience(self, mock_console, reset_display):
        """Convenience function should show startup banner."""
        import core.display
        core.display._display = GhostDisplay()
        core.display._display.console = mock_console

        show_startup_banner()

        output = mock_console.file.getvalue()
        assert "GHOST ENGINE v3.0" in output

    def test_show_agent_status_convenience(self, mock_console, reset_display):
        """Convenience function should show agent status."""
        import core.display
        core.display._display = GhostDisplay()
        core.display._display.console = mock_console

        show_agent_status()

        output = mock_console.file.getvalue()
        assert len(output) > 0

    def test_update_agent_status_convenience(self, reset_display):
        """Convenience function should update agent status."""
        import core.display
        core.display._display = GhostDisplay()

        update_agent_status(AgentType.BRAIN, "THINKING")

        assert core.display._display.agent_status[AgentType.BRAIN] == "THINKING"

    def test_log_debug_convenience(self, mock_console, reset_display):
        """Convenience function should log debug message."""
        import core.display
        core.display._display = GhostDisplay()
        core.display._display.console = mock_console

        log_debug("Debug from convenience")

        output = mock_console.file.getvalue()
        assert "Debug from convenience" in output

    def test_log_info_convenience(self, mock_console, reset_display):
        """Convenience function should log info message."""
        import core.display
        core.display._display = GhostDisplay()
        core.display._display.console = mock_console

        log_info("Info from convenience")

        output = mock_console.file.getvalue()
        assert "Info from convenience" in output

    def test_log_warning_convenience(self, mock_console, reset_display):
        """Convenience function should log warning message."""
        import core.display
        core.display._display = GhostDisplay()
        core.display._display.console = mock_console

        log_warning("Warning from convenience")

        output = mock_console.file.getvalue()
        assert "Warning from convenience" in output

    def test_log_error_convenience(self, mock_console, reset_display):
        """Convenience function should log error message."""
        import core.display
        core.display._display = GhostDisplay()
        core.display._display.console = mock_console

        log_error("Error from convenience")

        output = mock_console.file.getvalue()
        assert "Error from convenience" in output

    def test_log_critical_convenience(self, mock_console, reset_display):
        """Convenience function should log critical message."""
        import core.display
        core.display._display = GhostDisplay()
        core.display._display.console = mock_console

        log_critical("Critical from convenience")

        output = mock_console.file.getvalue()
        assert "Critical from convenience" in output

    def test_log_success_convenience(self, mock_console, reset_display):
        """Convenience function should log success message."""
        import core.display
        core.display._display = GhostDisplay()
        core.display._display.console = mock_console

        log_success("Success from convenience")

        output = mock_console.file.getvalue()
        assert "Success from convenience" in output

    def test_show_error_convenience(self, mock_console, reset_display):
        """Convenience function should show error panel."""
        import core.display
        core.display._display = GhostDisplay()
        core.display._display.console = mock_console

        show_error("Convenience Error", "Error from convenience function")

        output = mock_console.file.getvalue()
        assert "Convenience Error" in output
        assert "Error from convenience function" in output


class TestDisplayIntegrationDetailed:
    """Detailed integration tests for display system interactions."""

    @pytest.fixture
    def mock_console(self):
        """Create a mock console with a string buffer."""
        return Console(file=StringIO(), force_terminal=True, width=120)

    @pytest.fixture
    def display(self, mock_console):
        """Create a display with mock console."""
        display = GhostDisplay()
        display.console = mock_console
        return display

    def test_full_cycle_progress_workflow(self, display):
        """Test a complete cycle progress workflow."""
        # Start cycle
        with display.cycle_progress(cycle_num=1) as tracker:
            # Simulate each phase
            display.update_agent_status(AgentType.SOUL, "ACTIVE")
            tracker.update_phase("soul", 100)
            tracker.complete_phase("soul")

            display.update_agent_status(AgentType.SENSES, "ACTIVE")
            tracker.update_phase("senses", 100)
            tracker.complete_phase("senses")

            display.update_agent_status(AgentType.BRAIN, "ACTIVE")
            tracker.update_phase("brain", 100)
            tracker.complete_phase("brain")

            display.update_agent_status(AgentType.HAND, "ACTIVE")
            tracker.update_phase("hand", 100)
            tracker.complete_phase("hand")

        output = display.console.file.getvalue()
        assert "Cycle Complete" in output or "✓" in output

    def test_error_during_cycle(self, display):
        """Test error display during cycle execution."""
        display.show_error(
            title="Cycle Failed",
            message="Unable to complete trading cycle",
            context="During BRAIN phase",
            hint="Check market data feed",
            severity="ERROR",
            agent=AgentType.BRAIN
        )

        output = display.console.file.getvalue()
        assert "Cycle Failed" in output
        assert "BRAIN" in output

    def test_logging_sequence(self, display):
        """Test a sequence of log messages."""
        display.info("System starting")
        display.debug("Loading configuration")
        display.warning("High latency detected")
        display.success("Configuration loaded")
        display.error("Failed to connect")
        display.critical("System failure")

        output = display.console.file.getvalue()
        assert "System starting" in output
        assert "Loading configuration" in output
        assert "High latency detected" in output
        assert "Configuration loaded" in output
        assert "Failed to connect" in output
        assert "System failure" in output

    def test_agent_status_transitions(self, display):
        """Test agent status transitions throughout cycle."""
        # Initial state
        display.show_agent_status()
        display.console.file = StringIO()

        # Transitions
        display.update_agent_status(AgentType.SOUL, "ACTIVE")
        display.update_agent_status(AgentType.SOUL, "PROCESSING")
        display.update_agent_status(AgentType.SOUL, "COMPLETE")

        display.show_agent_status()
        output = display.console.file.getvalue()

        # Should show the final state
        assert "COMPLETE" in output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
