import pytest
import sys
import os
import asyncio
from unittest.mock import MagicMock, patch

from agents.senses import SensesAgent

@pytest.fixture
def senses_agent():
    bus = MagicMock()
    from unittest.mock import AsyncMock
    bus.publish = AsyncMock()
    bus.subscribe = AsyncMock()
    with patch.dict(os.environ, {}, clear=True):
        agent = SensesAgent(agent_id=2, bus=bus)
    yield agent

