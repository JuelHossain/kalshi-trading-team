import json
import os
from typing import Any

from agents.base import BaseAgent
from core.bus import EventBus
from core.constants import AGENT_NAME_TO_ID, FULL_AGENT_TO_PHASE
from core.event_formatter import format_gateway_log_event
from core.vault import RecursiveVault
from core.vault_utils import publish_vault_state


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
        await self.bus.subscribe("SYSTEM_ERROR", self.handle_error)  # Add error handler


    async def handle_system_log(self, message):

        payload = message.payload
        sender = payload.get("agent_name")
        agent_id = payload.get("agent_id", 0)

        # Pass logs to frontend with proper structure including phaseId and cycleId
        log_event = format_gateway_log_event(payload, 1, FULL_AGENT_TO_PHASE)
        await self.emit("LOG", log_event)

        # Update active agent in visualizer
        if sender not in ["GHOST", "GATEWAY", "HISTORIAN", "MECHANIC"]:
            await self.emit("STATE", {"activeAgentId": agent_id})

    async def on_tick(self, payload: dict[str, Any]):
        # Every cycle, we push a VAULT update and a STATE heartbeat
        await publish_vault_state(self.bus, self.vault, self.name)

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

    async def handle_error(self, message):
        """Handle SYSTEM_ERROR events from ErrorDispatcher"""
        from core.event_formatter import format_error_event

        error_data = message.payload

        # Format error for frontend using centralized formatter
        error_event = format_error_event(
            error_data,
            1,  # cycleId - will be updated by main.py
            FULL_AGENT_TO_PHASE,
            AGENT_NAME_TO_ID
        )

        await self.emit("ERROR", error_event)

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
        elif msg_type == "ERROR":
            bus_topic = "SYSTEM_ERROR"

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
                            if msg_type in ["VAULT", "SIMULATION", "HEALTH", "STATE", "ERROR"]
                            else "log"
                        ): data,
                    }
                )
            )
