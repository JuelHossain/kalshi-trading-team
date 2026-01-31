
import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock
from engine.agents.brain import BrainAgent
from engine.core.synapse import Synapse
from engine.core.bus import EventBus, Message

class TestCancelLogic(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.bus = AsyncMock(spec=EventBus)
        self.synapse = AsyncMock(spec=Synapse)
        self.synapse.opportunities = AsyncMock()
        self.brain = BrainAgent(3, self.bus, synapse=self.synapse)
        self.brain.log = AsyncMock()

    async def test_brain_stops_via_signal(self):
        """Test that Brain stops processing when STOP_AUTOPILOT is received"""
        
        # 1. Simulate STOP signal
        stop_msg = Message(topic="SYSTEM_CONTROL", payload={"action": "STOP_AUTOPILOT"}, sender="Test")
        await self.brain.on_system_control(stop_msg)
        
        self.assertTrue(self.brain.stop_requested, "Brain should have set stop_requested flag")
        
        # 2. Verify process_opportunities breaks loop
        # Mock queue to hold forever if not stopped
        self.synapse.opportunities.pop.side_effect = [None] 
        
        # This should return immediately because stop_requested is True (or set during loop)
        # We need to rely on the fact that if it DOESN'T check, it might loop if we fed it infinite items.
        # But here we just want to see the log message "Brain loop stopped..."
        
        await self.brain.process_opportunities(None)
        
        # Check logs
        stop_logs = [call for call in self.brain.log.call_args_list if "Brain loop stopped" in str(call)]
        self.assertTrue(len(stop_logs) > 0, "Brain should have logged stop message")

if __name__ == "__main__":
    unittest.main()
