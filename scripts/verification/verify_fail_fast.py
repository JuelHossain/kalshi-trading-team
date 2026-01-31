
import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock
from engine.main import GhostEngine
from engine.core.bus import Message

class TestFailFast(unittest.IsolatedAsyncioTestCase):
    async def test_system_fatal_triggers_shutdown(self):
        """Test that SYSTEM_FATAL event causes engine shutdown"""
        engine = GhostEngine()
        engine.bus = AsyncMock() # Mock the bus to capture publish events
        engine.shutdown = AsyncMock() # Mock shutdown to verify call
        
        # Verify initial state
        engine.running = True
        
        # Simulate SYSTEM_FATAL message
        fatal_msg = Message(topic="SYSTEM_FATAL", payload={"message": "Critical Failure"}, sender="TestAgent")
        
        # Call handler directly (simulating bus delivery)
        await engine._handle_system_fatal(fatal_msg)
        
        # Check results
        self.assertFalse(engine.running, "Engine should flag running=False")
        engine.shutdown.assert_awaited_once()
        print("Fail-Fast test passed: Engine shutdown triggered.")

if __name__ == "__main__":
    unittest.main()
