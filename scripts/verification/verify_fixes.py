
import asyncio
import unittest
from unittest.mock import MagicMock, AsyncMock
from engine.agents.brain import BrainAgent
from engine.core.synapse import Synapse, Opportunity, MarketData
from engine.core.bus import EventBus
import uuid

class TestBrainFixes(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.bus = AsyncMock(spec=EventBus)
        self.synapse = AsyncMock(spec=Synapse)
        self.synapse.opportunities = AsyncMock()
        self.brain = BrainAgent(3, self.bus, synapse=self.synapse)
        
        # Disable simulation for speed
        self.brain.run_simulation = MagicMock(return_value={"win_rate": 0.5, "ev": 0.5, "variance": 0.1})
        self.brain.log = AsyncMock()
        self.brain.log_error = AsyncMock()

    async def test_poison_pill_loop_detection(self):
        """Test that Brain detects and breaks infinite loops of the same ID"""
        opp_id = str(uuid.uuid4())
        opp = Opportunity(
            id=opp_id,
            ticker="LOOP_TEST",
            market_data=MarketData(ticker="LOOP_TEST", title="T", subtitle="S", yes_price=50, no_price=50, volume=100, expiration="2025")
        )

        # Mock queue returning the SAME item 5 times then None
        self.synapse.opportunities.pop.side_effect = [opp, opp, opp, opp, opp, None] 
        
        # Mock debate failing to ensure it stays in the loop logic (if it didn't break)
        self.brain.run_debate = AsyncMock(return_value={"confidence": 0, "reasoning": "Fail", "estimated_probability": 0.5})

        await self.brain.process_opportunities(None)

        # Verify critical error was logged
        critical_logs = [call for call in self.brain.log.call_args_list if "INFINITE LOOP DETECTED" in str(call)]
        self.assertTrue(len(critical_logs) > 0, "Brain should have logged INFINITE LOOP DETECTED")

    async def test_debate_error_handling(self):
        """Test that debate errors are caught and return veto properly"""
        opp = Opportunity(
            id=str(uuid.uuid4()),
            ticker="ERROR_TEST",
            market_data=MarketData(ticker="ERROR_TEST", title="T", subtitle="S", yes_price=50, no_price=50, volume=100, expiration="2025")
        )
        
        # Raise generic exception
        self.brain.client = MagicMock()
        self.brain.client.models.generate_content.side_effect = Exception("API BOOM")
        
        result = await self.brain.run_debate(opp.model_dump())
        
        self.assertEqual(result["confidence"], 0.0)
        self.assertIn("Debate failed", result["reasoning"])
         # Verify error was logged via dispatcher
        self.brain.log_error.assert_called()

if __name__ == "__main__":
    unittest.main()
