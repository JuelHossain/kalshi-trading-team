import asyncio
import os
import sys

from dotenv import load_dotenv

# Ensure engine path is in sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# Load environment
load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))

from agents.brain import BrainAgent
from core.bus import EventBus
from core.display import AgentType, get_display, log_info, log_warning, log_error, log_success
from core.synapse import Synapse

async def main():
    display = get_display()
    console = display.console

    console.print("[blue]==========================================[/]")
    console.print("[blue]    BRAIN AGENT - LIVE DIAGNOSTIC TAP     [/]")
    console.print("[blue]==========================================[/]")
    console.print("Source: Synapse Persistent Queue")
    console.print("Goal: Watch the Brain 'think' using real data\n")

    # 1. Setup Infrastructure
    bus = EventBus()
    synapse = Synapse(db_path="diagnostic_memory.db") # Connect to same DB as Senses

    # 2. Wire Monitor to Bus
    async def monitor_bus(msg):
        if msg.topic == "SYSTEM_LOG":
            level = msg.payload.get("level", "INFO")
            message = msg.payload.get("message", "")

            if level == "ERROR":
                log_error(f"[BRAIN ERROR] {message}", AgentType.BRAIN)
            elif "Analyzing" in message:
                console.print(f"\n[cyan]--- {message} ---[/]")
            else:
                log_info(message, AgentType.BRAIN)

        elif msg.topic == "EXECUTION_READY":
            ticker = msg.payload.get("ticker", "N/A")
            ev = msg.payload.get("ev", 0)
            console.print(f"\n[green]🎯 EXECUTION SIGNAL GENERATED![/]")
            console.print(f"[green]Target: {ticker} | EV Score: {ev:.4f}[/]")

        elif msg.topic == "SIM_RESULT":
            ticker = msg.payload.get("ticker")
            win_rate = msg.payload.get("win_rate", 0)
            veto = msg.payload.get("veto", False)
            status = "VETOED" if veto else "APPROVED"
            log_warning(f"[SIM] {ticker}: Win Rate {win_rate*100:.1f}% -> {status}", AgentType.BRAIN)

    await bus.subscribe("SYSTEM_LOG", monitor_bus)
    await bus.subscribe("EXECUTION_READY", monitor_bus)
    await bus.subscribe("SIM_RESULT", monitor_bus)

    # 3. Initialize Agent
    log_info("Initializing BrainAgent...", AgentType.BRAIN)
    brain = BrainAgent(3, bus, synapse=synapse)
    await brain.setup()

    # 4. Processing Loop
    log_info("Awaiting opportunities in Synapse...", AgentType.BRAIN)

    try:
        while True:
            # Check for data
            size = await synapse.opportunities.size()
            if size > 0:
                console.print(f"\n[SYNAPSE] Found {size} pending opportunities.")
                # Trigger process flow
                await bus.publish("OPPORTUNITIES_READY", {"count": size}, "DIAGNOSTIC")

            await asyncio.sleep(5) # Slow tick for diagnostics

    except KeyboardInterrupt:
        console.print("\n")
        log_warning("Stopping Brain Diagnostic...", AgentType.BRAIN)
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
