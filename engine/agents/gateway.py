import asyncio
import json
import os
from agents.base import BaseAgent
from core.bus import EventBus
from core.vault import RecursiveVault

class GatewayAgent(BaseAgent):
    """
    Agent 14: The Gateway (Bridge to Frontend)
    Role: Formats internal bus events into JSON for the TS Backend to broadcast.
    """
    
    def __init__(self, agent_id: int, bus: EventBus, vault: RecursiveVault):
        super().__init__("GATEWAY", agent_id, bus)
        self.vault = vault

    async def start(self):
        await self.log("Gateway Bridge Online. Routing events to stdout...")
        
        # Subscribe to critical topics
        await self.bus.subscribe("SYSTEM_LOG", self.handle_system_log)
        await self.bus.subscribe("SIM_RESULT", self.handle_sim)
        await self.bus.subscribe("SYSTEM_HEALTH", self.handle_health)
        await self.bus.subscribe("TICK", self.handle_tick)

    async def handle_system_log(self, message):
        sender = message.payload.get('agent_name')
        agent_id = message.payload.get('agent_id')
        
        # Pass logs to frontend
        self.emit("LOG", {
            "agentId": agent_id,
            "level": message.payload.get('level', 'INFO'),
            "message": message.payload.get('message')
        })

        # Update active agent in visualizer
        if sender not in ["GHOST", "GATEWAY", "HISTORIAN", "MECHANIC"]:
            self.emit("STATE", {
                "activeAgentId": agent_id
            })

    async def handle_tick(self, message):
        # Every cycle, we push a VAULT update and a STATE heartbeat
        vault_state = {
            "principal": self.vault.PRINCIPAL_CAPITAL_CENTS / 100,
            "currentProfit": (self.vault.current_balance - self.vault.start_of_day_balance) / 100,
            "lockThreshold": self.vault.DAILY_PROFIT_THRESHOLD_CENTS / 100,
            "isLocked": self.vault.is_locked,
            "total": self.vault.current_balance / 100
        }
        self.emit("VAULT", vault_state)
        
        # Heartbeat
        self.emit("STATE", {
            "cycleCount": message.payload.get('cycle'),
            "isProcessing": True
        })

    async def handle_sim(self, message):
        sim_data = {
            "ticker": message.payload.get('ticker'),
            "winRate": message.payload.get('win_rate'),
            "evScore": message.payload.get('ev'),
            "variance": 14, # Mock variance for now
            "iterations": 10, # 10k
            "veto": message.payload.get('veto', False)
        }
        self.emit("SIMULATION", sim_data)

    async def handle_health(self, message):
        self.emit("HEALTH", message.payload)

    def emit(self, msg_type: str, data: any):
        """Helper to print JSON to stdout for TS server capture."""
        if os.getenv("JSON_LOGS") == "true":
            print(json.dumps({
                "type": msg_type,
                "state" if msg_type in ["VAULT", "SIMULATION", "HEALTH", "STATE"] else "log": data
            }))
