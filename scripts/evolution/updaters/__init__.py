"""
Documentation updaters for the evolution system.

Each updater is responsible for updating a specific type of documentation
based on code changes detected by the analyzer.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from scripts.evolution.analyzer import ChangeAnalysis


class BaseUpdater(ABC):
    """Base class for all documentation updaters."""

    @abstractmethod
    def update(self, target: str, analysis: ChangeAnalysis) -> List[str]:
        """
        Update documentation based on analysis.

        Args:
            target: The documentation target path or identifier
            analysis: The change analysis

        Returns:
            List of updated file paths
        """
        pass

    @abstractmethod
    def can_handle(self, target: str) -> bool:
        """
        Check if this updater can handle the given target.

        Args:
            target: The documentation target

        Returns:
            True if this updater can handle the target
        """
        pass


__all__ = ['BaseUpdater']
