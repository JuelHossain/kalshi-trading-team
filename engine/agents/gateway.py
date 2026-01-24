import asyncio
import json
import os
from typing import Dict, Any
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

    # Agent to Phase mapping (mirrors shared/constants.ts)
    AGENT_TO_PHASE = {
        1: 0,
        11: 0,  # Phase 0: System Init
        2: 1,
        3: 1,
        7: 1,  # Phase 1: Surveillance
        4: 2,
        5: 2,
        6: 2,  # Phase 2: Intelligence
        8: 3,  # Phase 3: Execution
        9: 4,
        10: 4,  # Phase 4: Accounting
        12: 5,
        14: 5,  # Phase 5: Protection
        13: 13,  # Intervention
    }

    async def handle_system_log(self, message):
        from datetime import datetime

        payload = message.payload
        sender = payload.get("agent_name")
        agent_id = payload.get("agent_id", 0)
        phase_id = self.AGENT_TO_PHASE.get(agent_id, 0)

        # Pass logs to frontend with proper structure including phaseId and cycleId
        await self.emit(
            "LOG",
            {
                "id": f"log-{datetime.now().timestamp()}",
                "timestamp": payload.get("timestamp", datetime.now().isoformat()),
                "agentId": agent_id,
                "cycleId": 1,  # Will be updated by main.py cycle_count
                "phaseId": phase_id,
                "level": payload.get("level", "INFO"),
                "message": payload.get("message", ""),
            },
        )

        # Update active agent in visualizer
        if sender not in ["GHOST", "GATEWAY", "HISTORIAN", "MECHANIC"]:
            await self.emit("STATE", {"activeAgentId": agent_id})

    async def on_tick(self, payload: Dict[str, Any]):
        # Every cycle, we push a VAULT update and a STATE heartbeat
        vault_state = {
            "principal": self.vault.PRINCIPAL_CAPITAL_CENTS / 100,
            "currentProfit": (self.vault.current_balance - self.vault.start_of_day_balance) / 100,
            "lockThreshold": self.vault.DAILY_PROFIT_THRESHOLD_CENTS / 100,
            "isLocked": self.vault.is_locked,
            "total": self.vault.current_balance / 100,
        }
        await self.emit("VAULT", vault_state)

        # Heartbeat
        await self.emit("STATE", {"cycleCount": payload.get("cycle"), "isProcessing": True})

    async def handle_sim(self, message):
        payload = message.payload
        sim_data = {
            "ticker": payload.get("ticker"),
            "winRate": payload.get("win_rate"),
            "evScore": payload.get("ev_score"),  # Checked analyst/sim_scientist payload
            "variance": payload.get("variance", 0),
            "iterations": payload.get("iterations", 0),
            "veto": payload.get("veto", False),
        }
        await self.emit("SIMULATION", sim_data)

    async def handle_health(self, message):
        await self.emit("HEALTH", message.payload)

    async def emit(self, msg_type: str, data: Any):
        """Helper to print JSON to stdout and publish to bus for SSE streaming."""
        # Wrap for bus if needed
        bus_topic = None
        if msg_type == "VAULT":
            bus_topic = "VAULT_UPDATE"
        elif msg_type == "SIMULATION":
            bus_topic = "SIM_RESULT"
        elif msg_type == "HEALTH":
            bus_topic = "SYSTEM_HEALTH"
        elif msg_type == "STATE":
            bus_topic = "SYSTEM_STATE"

        if bus_topic:
            await self.bus.publish(bus_topic, data, self.name)

        if os.getenv("JSON_LOGS") == "true":
            # Direct print here because this IS the gateway output channel
            print(
                json.dumps(
                    {
                        "type": msg_type,
                        (
                            "state"
                            if msg_type in ["VAULT", "SIMULATION", "HEALTH", "STATE"]
                            else "log"
                        ): data,
                    }
                )
            )
