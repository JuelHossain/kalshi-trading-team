import asyncio
import os
import sys

from dotenv import load_dotenv

# Ensure engine path is in sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# Load environment
load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))

from agents.hand import HandAgent
from core.bus import EventBus
from core.display import AgentType, get_display, log_info, log_success, log_error
from core.synapse import ExecutionSignal, MarketData, Opportunity, Synapse
from core.vault import RecursiveVault

async def main():
    display = get_display()
    console = display.console

    console.print("[green]==========================================[/]")
    console.print("[green]     HAND AGENT - LIVE DIAGNOSTIC TAP      [/]")
    console.print("[green]==========================================[/]")
    console.print("Goal: Inject signal into Synapse and watch Hand strike\n")

    # 1. Setup Infrastructure
    bus = EventBus()
    synapse = Synapse(db_path="diagnostic_memory.db")
    vault = RecursiveVault()
    await vault.initialize(30000) # $300 balance

    # 2. Wire Monitor
    async def monitor_bus(msg):
        if msg.topic == "SYSTEM_LOG":
            message = msg.payload.get("message", "")
            if "Target acquired" in message:
                console.print(f"[cyan]--- {message} ---[/]")
            else:
                log_info(message, AgentType.HAND)
        elif msg.topic == "TRADE_RESULT":
             console.print(f"\n[green]✅ TRADE_RESULT EVENT EMITTED for {msg.payload.get('ticker')}[/]")

    await bus.subscribe("SYSTEM_LOG", monitor_bus)
    await bus.subscribe("TRADE_RESULT", monitor_bus)

    # 3. Inject Mock Signal
    log_info("Injecting mock ExecutionSignal into Synapse...", AgentType.HAND)
    m_data = MarketData(
        ticker="DIAG-TEST-TICKER",
        title="Diagnostic Test",
        subtitle="Verification Market",
        yes_price=50,
        no_price=50,
        volume=1000,
        expiration="2026-12-31T23:59:59Z"
    )
    opp = Opportunity(ticker="DIAG-TEST-TICKER", market_data=m_data)
    signal = ExecutionSignal(
        target_opportunity=opp,
        confidence=0.92,
        monte_carlo_ev=0.15,
        reasoning="Diagnostic check successful.",
        suggested_count=20
    )
    await synapse.executions.push(signal)
    console.print(f"Signal injected. Synapse Pending Executions: {await synapse.executions.size()}\n")

    # 4. Initialize Hand
    log_info("Initializing HandAgent...", AgentType.HAND)
    hand = HandAgent(4, bus, vault, synapse=synapse)
    await hand.setup()

    # 5. Trigger Loop
    log_info("Triggering EXECUTION_READY signal...", AgentType.HAND)
    await bus.publish("EXECUTION_READY", {"ticker": "DIAG-TEST-TICKER"}, "DIAGNOSTIC")

    # Wait for processing
    await asyncio.sleep(5)

    # Check if signal was popped
    remaining = await synapse.executions.size()
    console.print(f"\nRemaining signals in Synapse: {remaining}")
    if remaining == 0:
        log_success("PASSED: HandAgent consumed the signal from Synapse.", AgentType.HAND)
    else:
        log_error("FAILED: Signal still in queue.", AgentType.HAND)

if __name__ == "__main__":
    asyncio.run(main())
