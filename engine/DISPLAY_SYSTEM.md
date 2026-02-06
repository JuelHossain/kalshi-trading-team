# Ghost Engine v3.0 - Rich Display System

A modern, beautiful CLI display system powered by the Rich library for the Ghost Engine's 4 Mega-Agent Architecture.

## Features

### 1. Startup Banner
Beautiful Ghost Engine v3.0 banner with information about all 4 Mega-Agents:
- SOUL - System, Memory & Evolution
- SENSES - Surveillance & Signal Detection
- BRAIN - Intelligence & Mathematical Verification
- HAND - Precision Strike & Budget Sentinel

### 2. Step-by-Step Progress
Visual progress bars for trading cycles showing each phase:
- SOUL: Authorization & Setup
- SENSES: Market Surveillance
- BRAIN: Intelligence Analysis
- HAND: Execution & Trading

### 3. AI Thinking Display
Animated spinners showing agent work in progress with contextual messages.

### 4. Agent Status Table
Real-time status display of all 4 agents with:
- Current state (IDLE, ACTIVE, PROCESSING, ERROR, etc.)
- Last activity timestamp
- Current cycle number

### 5. Error Display
Beautiful error panels with:
- Error title and message
- Context information
- Helpful hints
- Severity levels (WARNING, ERROR, CRITICAL)
- Agent association

### 6. Live Dashboard
Real-time monitoring dashboard with:
- Agent status panel
- Activity feed
- System information
- Auto-refreshing layout

### 7. Log Levels
Visual distinction for different log levels:
- DEBUG (cyan) - Detailed diagnostic information
- INFO (white) - General informational messages
- WARNING (yellow) - Warning messages
- ERROR (red) - Error messages
- CRITICAL (bold red) - Critical error messages
- SUCCESS (green) - Success messages

## Installation

Add Rich to your requirements:

```bash
pip install rich>=13.0.0
```

Or update `engine/requirements.txt`:

```
rich>=13.0.0  # Modern CLI display system
```

## Usage

### Basic Usage

```python
from core.display import (
    show_startup_banner,
    log_info,
    log_error,
    log_success,
    AgentType,
)

# Show startup banner
show_startup_banner()

# Log messages
log_info("System starting up...")
log_success("Agent initialized successfully", AgentType.BRAIN)
log_error("Failed to fetch market data", AgentType.SENSES)
```

### Advanced Usage

```python
from core.display import GhostDisplay, AgentType

# Get display instance
display = get_display()

# Update agent status
display.update_agent_status(AgentType.BRAIN, "THINKING")

# Show error with context
display.show_error(
    title="Connection Failed",
    message="Could not connect to Kalshi API",
    context="Network request timed out after 30 seconds",
    hint="Check your internet connection",
    severity="ERROR",
    agent=AgentType.GATEWAY
)

# Use progress tracking
with display.cycle_progress(1, is_paper_trading=True) as progress:
    # SOUL phase
    progress.update_phase("soul", 50)
    # ... do work ...
    progress.complete_phase("soul")

    # SENSES phase
    progress.update_phase("senses", 50)
    # ... do work ...
    progress.complete_phase("senses")

    # BRAIN phase
    progress.update_phase("brain", 50)
    # ... do work ...
    progress.complete_phase("brain")

    # HAND phase
    progress.update_phase("hand", 50)
    # ... do work ...
    progress.complete_phase("hand")

# Use agent thinking animation
with display.agent_thinking(AgentType.BRAIN, "Running simulation..."):
    # ... do work ...
    pass
```

## API Reference

### GhostDisplay Class

Main display manager for Ghost Engine.

#### Methods

- `show_startup_banner()` - Display the Ghost Engine startup banner
- `show_agent_status()` - Display current agent status table
- `update_agent_status(agent: AgentType, status: str)` - Update agent status
- `cycle_progress(cycle_num: int, is_paper_trading: bool)` - Context manager for cycle progress
- `agent_thinking(agent: AgentType, action: str)` - Context manager for agent thinking animation
- `show_error(title, message, context, hint, severity, agent)` - Display error panel
- `log(level, message, agent)` - Log a message with visual distinction
- `debug/info/warning/error/critical/success(message, agent)` - Convenience logging methods

### AgentType Enum

Enum representing the 4 Mega-Agents:

- `AgentType.SOUL` - System, Memory & Evolution
- `AgentType.SENSES` - Surveillance & Signal Detection
- `AgentType.BRAIN` - Intelligence & Mathematical Verification
- `AgentType.HAND` - Precision Strike & Budget Sentinel
- `AgentType.GATEWAY` - HTTP Interface & External Communication

### Convenience Functions

- `get_display()` - Get the global GhostDisplay instance
- `show_startup_banner()` - Show startup banner
- `show_agent_status()` - Show agent status table
- `update_agent_status(agent, status)` - Update agent status
- `log_debug/info/warning/error/critical/success(message, agent)` - Quick logging
- `show_error(title, message, context, hint, severity, agent)` - Show error panel

## Integration with Existing Code

### Updating Logger

The `core/logger.py` has been enhanced to integrate with the Rich display system while maintaining backward compatibility:

```python
from core.logger import get_logger, AgentType

# Get logger with agent association
logger = get_logger("MY_AGENT", agent=AgentType.BRAIN)

# Use standard logging methods
logger.info("This will be displayed with Rich formatting")
logger.error("This will show in the Rich error format")
logger.success("Custom success level with Rich formatting")
```

### Updating Main Engine

The `engine/main.py` has been updated to use the Rich display system:

```python
from core.display import (
    GhostDisplay,
    AgentType,
    show_startup_banner,
    update_agent_status,
    log_info,
    log_success,
)

class GhostEngine:
    def __init__(self):
        # ... existing code ...
        self.display: GhostDisplay = get_display()

    async def initialize_system(self):
        # Show Rich startup banner
        show_startup_banner()

        # Use Rich logging
        log_info("Initializing Ghost Engine v3.0 system components...")

        # Update agent status
        update_agent_status(AgentType.SOUL, "INITIALIZING")

        # ... existing code ...

        log_success("SOUL initialized successfully", AgentType.SOUL)
        update_agent_status(AgentType.SOUL, "IDLE")
```

## Windows Compatibility

The display system is fully compatible with Windows. The Rich library automatically handles Windows terminal limitations and provides appropriate rendering.

## Testing

Run the display system tests:

```bash
pytest tests/engine/core/test_display.py -v
```

Run the display system demo:

```bash
python engine/demo_display.py
```

## Design Principles

1. **Minimal Code** - Leverages Rich's built-in features for maximum functionality with minimum code
2. **Modern Design** - Clean, professional interface similar to Claude Code/Gemini CLI
3. **Emoji Support** - Visual indicators using emojis for better user experience
4. **Color Coding** - Consistent color scheme:
   - Cyan for agents
   - Green for success
   - Red for errors
   - Yellow for warnings
5. **Context Manager Pattern** - Uses Python context managers for automatic resource management
6. **Windows Compatible** - Works seamlessly on Windows terminals
7. **Backward Compatible** - Existing logger code continues to work

## Troubleshooting

### Rich not installed

If you get an import error for Rich, install it:

```bash
pip install rich>=13.0.0
```

### Emoji display issues on Windows

The display system automatically handles emoji limitations on Windows by falling back to text-only mode when needed.

### Color display issues

If colors are not displaying correctly:
- Ensure your terminal supports color output
- Try using a modern terminal like Windows Terminal, iTerm2, or GNOME Terminal
- Check that Rich is up to date

## Contributing

When contributing to the display system:

1. Follow the existing code style
2. Add tests for new features
3. Update the demo script to showcase new features
4. Maintain Windows compatibility
5. Keep it minimal - leverage Rich's built-in features

## License

Part of the Ghost Engine v3.0 project.
