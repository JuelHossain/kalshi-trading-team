"""
GHOST ENGINE v3.0 - 4 MEGA-AGENT ARCHITECTURE
Codename: Sentient Alpha (Consolidated)

The 4 Pillars of Profit:
1. SOUL - System, Memory & Evolution
2. SENSES - Surveillance & Signal Detection
3. BRAIN - Intelligence & Mathematical Verification
4. HAND - Precision Strike & Budget Sentinel

Enhanced with Rich display system for beautiful CLI output.
"""

import logging
import os
import re
import sys
from typing import Optional

# Import Rich display system
try:
    from core.display import AgentType, get_display
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    # Create a dummy AgentType for fallback
    class AgentType:
        SOUL = 1
        SENSES = 2
        BRAIN = 3
        HAND = 4
        GATEWAY = 5

# Pre-compile regex for performance (Emoji stripping)
EMOJI_PATTERN = re.compile("["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map symbols
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "]+", flags=re.UNICODE)


class EmojiSafeFormatter(logging.Formatter):
    """
    Enhanced formatter that strips emojis for Windows compatibility and adds colors.
    Integrates with Rich display system when available.
    """

    FORMATS = {
        logging.DEBUG: "\033[36m[%(levelname)s] %(message)s\033[0m",  # Cyan
        logging.INFO: "\033[37m[%(levelname)s] %(message)s\033[0m",  # White
        logging.WARNING: "\033[33m[%(levelname)s] %(message)s\033[0m",  # Yellow
        logging.ERROR: "\033[31m[%(levelname)s] %(message)s\033[0m",  # Red
        logging.CRITICAL: "\033[1;31m[%(levelname)s] 💀 %(message)s\033[0m",  # Bold Red
    }

    def format(self, record):
        # 1. Strip Emojis if on Windows (or forced)
        if os.name == "nt":
             if isinstance(record.msg, str):
                record.msg = EMOJI_PATTERN.sub("", record.msg)

        # 2. Add Color (using ANSI codes directly instead of colorama)
        log_fmt = self.FORMATS.get(record.levelno, self.FORMATS[logging.INFO])
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


class RichIntegratedLogger:
    """
    A logger that integrates with the Rich display system while maintaining
    backward compatibility with the standard logging interface.
    """

    def __init__(self, name: str):
        self.name = name
        self._logger = logging.getLogger(name)
        self._agent: Optional[AgentType] = None

        # Configure standard logger if not already configured
        if not self._logger.handlers:
            self._logger.setLevel(logging.DEBUG)
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(EmojiSafeFormatter())
            self._logger.addHandler(handler)

    def set_agent(self, agent: AgentType) -> None:
        """Associate this logger with a specific agent for Rich display."""
        self._agent = agent

    def debug(self, message: str, *args, **kwargs):
        """Log debug message."""
        self._logger.debug(message, *args, **kwargs)
        if RICH_AVAILABLE:
            get_display().debug(message, self._agent)

    def info(self, message: str, *args, **kwargs):
        """Log info message."""
        self._logger.info(message, *args, **kwargs)
        if RICH_AVAILABLE:
            get_display().info(message, self._agent)

    def warning(self, message: str, *args, **kwargs):
        """Log warning message."""
        self._logger.warning(message, *args, **kwargs)
        if RICH_AVAILABLE:
            get_display().warning(message, self._agent)

    def error(self, message: str, *args, **kwargs):
        """Log error message."""
        self._logger.error(message, *args, **kwargs)
        if RICH_AVAILABLE:
            get_display().error(message, self._agent)

    def critical(self, message: str, *args, **kwargs):
        """Log critical message."""
        self._logger.critical(message, *args, **kwargs)
        if RICH_AVAILABLE:
            get_display().critical(message, self._agent)

    def success(self, message: str, *args, **kwargs):
        """Log success message (custom level)."""
        # Log as info to standard logger
        self._logger.info(f"✅ {message}", *args, **kwargs)
        if RICH_AVAILABLE:
            get_display().success(message, self._agent)

    def exception(self, message: str, *args, **kwargs):
        """Log exception with traceback."""
        self._logger.exception(message, *args, **kwargs)
        if RICH_AVAILABLE:
            get_display().error(f"{message} (see traceback)", self._agent)


def get_logger(name: str, agent: Optional[AgentType] = None) -> RichIntegratedLogger:
    """
    Factory to return a configured logger with Rich integration.

    Args:
        name: Logger name
        agent: Optional AgentType to associate with this logger

    Returns:
        RichIntegratedLogger instance
    """
    logger = RichIntegratedLogger(name)
    if agent is not None:
        logger.set_agent(agent)
    return logger


# Global instance for easy access (backward compatibility)
logger = get_logger("GHOST")


# Convenience functions for quick access
def log_debug(message: str, agent: Optional[AgentType] = None) -> None:
    """Log a debug message."""
    if RICH_AVAILABLE:
        get_display().debug(message, agent)
    else:
        logger.debug(message)


def log_info(message: str, agent: Optional[AgentType] = None) -> None:
    """Log an info message."""
    if RICH_AVAILABLE:
        get_display().info(message, agent)
    else:
        logger.info(message)


def log_warning(message: str, agent: Optional[AgentType] = None) -> None:
    """Log a warning message."""
    if RICH_AVAILABLE:
        get_display().warning(message, agent)
    else:
        logger.warning(message)


def log_error(message: str, agent: Optional[AgentType] = None) -> None:
    """Log an error message."""
    if RICH_AVAILABLE:
        get_display().error(message, agent)
    else:
        logger.error(message)


def log_critical(message: str, agent: Optional[AgentType] = None) -> None:
    """Log a critical message."""
    if RICH_AVAILABLE:
        get_display().critical(message, agent)
    else:
        logger.critical(message)


def log_success(message: str, agent: Optional[AgentType] = None) -> None:
    """Log a success message."""
    if RICH_AVAILABLE:
        get_display().success(message, agent)
    else:
        logger.info(f"✅ {message}")


__all__ = [
    "get_logger",
    "RichIntegratedLogger",
    "logger",
    "log_debug",
    "log_info",
    "log_warning",
    "log_error",
    "log_critical",
    "log_success",
]
