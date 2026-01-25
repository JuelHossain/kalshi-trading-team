import asyncio
import os
import sys

from colorama import Fore, Style, init
from dotenv import load_dotenv

# Ensure engine path is in sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# Load environment
load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))

from agents.senses import SensesAgent
from core.bus import EventBus
from core.network import kalshi_client
from core.synapse import Synapse

# Initialize Colorama
init()

async def main():
    print(f"{Fore.CYAN}=========================================={Style.RESET_ALL}")
    print(f"{Fore.CYAN}   SENSES AGENT - LIVE DIAGNOSTIC TAP     {Style.RESET_ALL}")
    print(f"{Fore.CYAN}=========================================={Style.RESET_ALL}")
    print("Target: Real Kalshi Sandbox API")
    print("Goal: Watch Senses 'Seeing' the market\n")

    # 1. Setup Infrastructure
    bus = EventBus()
    synapse = Synapse(db_path="diagnostic_memory.db")
    
    # 2. Wire Monitor to Bus
    async def monitor_bus(msg):
        if msg.topic == "SYSTEM_LOG":
            # Filter low level
            if msg.payload.get("level") == "INFO" and "Selected" not in msg.payload.get("message", ""):
                return
            
            color = Fore.GREEN if msg.payload.get("level") == "INFO" else Fore.YELLOW
            print(f"{color}[LOG] {msg.payload.get('message')}{Style.RESET_ALL}")
            
        elif msg.topic == "OPPORTUNITIES_READY":
            count = msg.payload.get("count", 0)
            top = msg.payload.get("top", {})
            ticker = top.get("ticker", "N/A")
            vol = top.get("volume", 0)
            print(f"\n{Fore.MAGENTA}>>> OPPORTUNITY BATCH DETECTED: {count} Items{Style.RESET_ALL}")
            print(f"{Fore.MAGENTA}>>> Top Candidate: {ticker} (Vol: {vol}){Style.RESET_ALL}\n")

    await bus.subscribe("SYSTEM_LOG", monitor_bus)
    await bus.subscribe("OPPORTUNITIES_READY", monitor_bus)

    # 3. Initialize Agent
    print("Initializing SensesAgent...")
    senses = SensesAgent(2, bus, kalshi_client=kalshi_client, synapse=synapse)
    
    # Check Connectivity
    print("Checking connection to Kalshi API...")
    balance_cents = await kalshi_client.get_balance()
    print(f"Connection successful. Balance: ${balance_cents/100:.2f}")

    # 4. Run Senses
    await senses.setup()
    
    # Trigger scan loop manually
    print(f"{Fore.GREEN}Starting Surveillance Loop...{Style.RESET_ALL}")
    
    # We call the internal loop method directly to bypass "PREFLIGHT_COMPLETE" trigger requirements
    # or we can publish it. Let's publish it to simulate real flow.
    await bus.publish("PREFLIGHT_COMPLETE", {}, "DIAGNOSTIC")

    # Keep alive (Push Only Mode)
    try:
        while True:
            await asyncio.sleep(2)
            # Check Synapse Queue Size
            q_size = await synapse.opportunities.size()
            print(f"[SYNAPSE] Pending Opportunities in DB: {q_size}   ", end="\r")
            
            # Note: We do NOT pop here anymore, so Brain can test consuming them.
            # item = await synapse.opportunities.pop() ...
                    
    except KeyboardInterrupt:
        print(f"\n{Fore.RED}Stopping Diagnostic...{Style.RESET_ALL}")
        await senses.stop_scan({})
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
