import asyncio
import os
import sys

from dotenv import load_dotenv

# Ensure engine path is in sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# Load environment
load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))

from agents.senses import SensesAgent
from core.bus import EventBus
from core.display import AgentType, get_display, log_info, log_warning, log_error, log_success
from core.network import kalshi_client
from core.synapse import Synapse

async def main():
    display = get_display()
    console = display.console

    console.print("[cyan]==========================================[/]")
    console.print("[cyan]   SENSES AGENT - LIVE DIAGNOSTIC TAP     [/]")
    console.print("[cyan]==========================================[/]")
    console.print("Target: Real Kalshi Sandbox API")
    console.print("Goal: Watch Senses 'Seeing' the market\n")

    # 1. Setup Infrastructure
    bus = EventBus()
    synapse = Synapse(db_path="diagnostic_memory.db")

    # 2. Wire Monitor to Bus
    async def monitor_bus(msg):
        if msg.topic == "SYSTEM_LOG":
            # Filter low level
            if msg.payload.get("level") == "INFO" and "Selected" not in msg.payload.get("message", ""):
                return

            level = msg.payload.get("level")
            message = msg.payload.get("message")
            if level == "INFO":
                log_info(message, AgentType.SENSES)
            else:
                log_warning(message, AgentType.SENSES)

        elif msg.topic == "OPPORTUNITIES_READY":
            count = msg.payload.get("count", 0)
            top = msg.payload.get("top", {})
            ticker = top.get("ticker", "N/A")
            vol = top.get("volume", 0)
            console.print(f"\n[magenta]>>> OPPORTUNITY BATCH DETECTED: {count} Items[/]")
            console.print(f"[magenta]>>> Top Candidate: {ticker} (Vol: {vol})[/]\n")

    await bus.subscribe("SYSTEM_LOG", monitor_bus)
    await bus.subscribe("OPPORTUNITIES_READY", monitor_bus)

    # 3. Initialize Agent
    log_info("Initializing SensesAgent...", AgentType.SENSES)
    senses = SensesAgent(2, bus, kalshi_client=kalshi_client, synapse=synapse)

    # Check Connectivity
    log_info("Checking connection to Kalshi API...", AgentType.SENSES)
    balance_cents = await kalshi_client.get_balance()
    log_success(f"Connection successful. Balance: ${balance_cents/100:.2f}", AgentType.SENSES)

    # 4. Run Senses
    await senses.setup()

    # Trigger scan loop manually
    log_info("Starting Surveillance Loop...", AgentType.SENSES)

    # We call the internal loop method directly to bypass "PREFLIGHT_COMPLETE" trigger requirements
    # or we can publish it. Let's publish it to simulate real flow.
    await bus.publish("PREFLIGHT_COMPLETE", {}, "DIAGNOSTIC")

    # Keep alive (Push Only Mode)
    try:
        while True:
            await asyncio.sleep(2)
            # Check Synapse Queue Size
            q_size = await synapse.opportunities.size()
            console.print(f"[SYNAPSE] Pending Opportunities in DB: {q_size}   ", end="\r")

            # Note: We do NOT pop here anymore, so Brain can test consuming them.
            # item = await synapse.opportunities.pop() ...

    except KeyboardInterrupt:
        console.print("\n")
        log_warning("Stopping Diagnostic...", AgentType.SENSES)
        await senses.stop_scan({})
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
