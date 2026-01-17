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

    async def setup(self):
        await self.log("Gateway Bridge Online. Routing events to stdout...")
        
        # Subscribe to critical topics
        await self.bus.subscribe("SYSTEM_LOG", self.handle_system_log)
        await self.bus.subscribe("SIM_RESULT", self.handle_sim)
        await self.bus.subscribe("SYSTEM_HEALTH", self.handle_health)

    async def handle_system_log(self, message):
        payload = message.payload
        sender = payload.get('agent_name')
        agent_id = payload.get('agent_id')
        
        # Pass logs to frontend
        self.emit("LOG", {
            "agentId": agent_id,
            "level": payload.get('level', 'INFO'),
            "message": payload.get('message')
        })

        # Update active agent in visualizer
        if sender not in ["GHOST", "GATEWAY", "HISTORIAN", "MECHANIC"]:
            self.emit("STATE", {
                "activeAgentId": agent_id
            })

    async def on_tick(self, payload: Dict[str, Any]):
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
            "cycleCount": payload.get('cycle'),
            "isProcessing": True
        })

    async def handle_sim(self, message):
        payload = message.payload
        sim_data = {
            "ticker": payload.get('ticker'),
            "winRate": payload.get('win_rate'),
            "evScore": payload.get('ev_score'), # Checked analyst/sim_scientist payload
            "variance": payload.get('variance', 0),
            "iterations": payload.get('iterations', 0),
            "veto": payload.get('veto', False)
        }
        self.emit("SIMULATION", sim_data)

    async def handle_health(self, message):
        self.emit("HEALTH", message.payload)

    def emit(self, msg_type: str, data: Any):
        """Helper to print JSON to stdout for TS server capture."""
        if os.getenv("JSON_LOGS") == "true":
            # Direct print here because this IS the gateway output channel
            print(json.dumps({
                "type": msg_type,
                "state" if msg_type in ["VAULT", "SIMULATION", "HEALTH", "STATE"] else "log": data
            }))
