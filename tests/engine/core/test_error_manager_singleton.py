"""Regression tests for the global ErrorManager accessor.

`get_error_manager()` assigned to `_global_error_manager` without declaring it
`global`, which made the name function-local and raised UnboundLocalError on
every call. Since `BaseAgent.__init__` calls it whenever no manager is injected,
no agent could be constructed.
"""

import pytest
from core.error_manager import ErrorManager, get_error_manager, set_error_manager


@pytest.fixture(autouse=True)
def _reset_global():
    """Keep the module-level singleton from leaking between tests."""
    import core.error_manager as em

    original = em._global_error_manager
    em._global_error_manager = None
    yield
    em._global_error_manager = original


def test_get_error_manager_does_not_raise_unbound_local():
    """The original bug: this raised UnboundLocalError unconditionally."""
    assert isinstance(get_error_manager(), ErrorManager)


def test_get_error_manager_is_singleton():
    assert get_error_manager() is get_error_manager()


def test_set_error_manager_is_observed_by_get():
    injected = ErrorManager()
    set_error_manager(injected)
    assert get_error_manager() is injected


def test_agent_constructs_without_injected_manager():
    """BaseAgent falls back to get_error_manager(); this was the real-world impact."""
    from agents.base import BaseAgent
    from core.bus import EventBus

    agent = BaseAgent("test-agent", 1, EventBus())
    assert isinstance(agent.error_manager, ErrorManager)
