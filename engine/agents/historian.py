import os
import json
import asyncio
from typing import Dict, Any
from agents.base import BaseAgent
from core.bus import EventBus

class HistorianAgent(BaseAgent):
    """
    Agent 10: The Historian
    Role: Reflexive Memory & Data Persistence.
    Saves message bus history and trade logs to Supabase/Local.
    """
    
    def __init__(self, agent_id: int, bus: EventBus):
        super().__init__("HISTORIAN", agent_id, bus)
        self.log_file = "engine/history.log"

    async def start(self):
        await self.log("Historian Archive Online. Log: engine/history.log")
        
        # Subscribe to all major events for archiving
        topics = ["AUDIT_DECISION", "TRADE_EXECUTED", "MARKET_DATA", "SYSTEM_LOG"]
        for topic in topics:
            await self.bus.subscribe(topic, self.archive_event)

    async def archive_event(self, message):
        timestamp = message.timestamp
        sender = message.sender
        topic = message.topic
        payload = message.payload
        
        entry = f"[{timestamp}] [{sender}] {topic}: {json.dumps(payload)}\n"
        
        # Async write to log file
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self.write_to_disk, entry)

    def write_to_disk(self, text: str):
        with open(self.log_file, "a") as f:
            f.write(text)
            
    async def get_recent_alpha(self, ticker: str):
        # In prod, this queries Supabase for historical performance of this ticker
        return {"success_rate": 0.65}
