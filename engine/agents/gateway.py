"""Relay bus events outward for the dashboard.

Subscribes to log, simulation, health and error topics and formats them
for the SSE stream and, when JSON_LOGS is set, for stdout. It publishes
only what it originates itself (VAULT_UPDATE and SYSTEM_STATE from
on_tick). Republishing a relayed topic re-invokes this agent's own
handler, and because publish awaits every subscriber that never returns.
"""

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

    def __init__(self, agent_id: int, bus: EventBus, vault: RecursiveVault, error_manager=None):
        super().__init__("GATEWAY", agent_id, bus, error_manager=error_manager)
        self.vault = vault

    async def setup(self):
        """Subscribe to the topics this agent relays outward."""
        await self.log("Gateway Bridge Online. Routing events to stdout...")

        # Subscribe to critical topics
        await self.bus.subscribe("SYSTEM_LOG", self.handle_system_log)
        await self.bus.subscribe("SIM_RESULT", self.handle_sim)
        await self.bus.subscribe("SYSTEM_HEALTH", self.handle_health)
        await self.bus.subscribe("SYSTEM_ERROR", self.handle_error)  # Add error handler

    async def handle_system_log(self, message):
        """Shape a SYSTEM_LOG event for the dashboard and emit it."""

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
        """Publish vault state and a STATE heartbeat once per tick."""
        # Every cycle, we push a VAULT update and a STATE heartbeat
        await publish_vault_state(self.bus, self.vault, self.name)

        # Heartbeat
        await self.emit("STATE", {"cycleCount": payload.get("cycle"), "isProcessing": True})

    async def handle_sim(self, message):
        """Relay a Brain simulation result outward. Never republished to the bus."""
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
        """Relay a health report outward. Never republished to the bus."""
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
            AGENT_NAME_TO_ID,
        )

        await self.emit("ERROR", error_event)

    async def emit(self, msg_type: str, data: Any):
        """Print JSON to stdout, and publish to the bus only what this agent originates.

        Only VAULT and STATE go back onto the bus. They are produced here, in
        on_tick, and the HTTP layer subscribes to them.

        SIMULATION, HEALTH and ERROR must not. This agent *receives* them from
        the bus (SIM_RESULT, SYSTEM_HEALTH, SYSTEM_ERROR) and used to republish
        each one under the same topic -- which re-invoked this agent's own
        handler, which republished it again. Because EventBus.publish awaits
        every subscriber, the original publisher never got its await back.
        That was the Brain: its very next line after "AI Prob: ..." is a
        SIM_RESULT publish, and no decision was ever logged after it. The
        engine reported healthy the whole time.

        The relay-to-bus existed for a Node backend that read this process's
        stdout. The HTTP server now subscribes to the bus directly, so
        republishing relayed events is not just looping, it is redundant.
        """
        ORIGINATED_HERE = {"VAULT": "VAULT_UPDATE", "STATE": "SYSTEM_STATE"}
        bus_topic = ORIGINATED_HERE.get(msg_type)

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
