"""Senses Agent - Surveillance & Signal Detection"""

# Try to import ddgs, set availability flag
try:
    from ddgs import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False
    DDGS = None

from .agent import SensesAgent

__all__ = ["SensesAgent", "DDGS_AVAILABLE"]
