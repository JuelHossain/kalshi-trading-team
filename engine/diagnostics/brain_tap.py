import asyncio
import os
import sys

from colorama import Fore, Style, init
from dotenv import load_dotenv

# Ensure engine path is in sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# Load environment
load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))

from agents.brain import BrainAgent
from core.bus import EventBus
from core.synapse import Synapse

# Initialize Colorama
init()

async def main():
    print(f"{Fore.BLUE}=========================================={Style.RESET_ALL}")
    print(f"{Fore.BLUE}    BRAIN AGENT - LIVE DIAGNOSTIC TAP     {Style.RESET_ALL}")
    print(f"{Fore.BLUE}=========================================={Style.RESET_ALL}")
    print("Source: Synapse Persistent Queue")
    print("Goal: Watch the Brain 'think' using real data\n")

    # 1. Setup Infrastructure
    bus = EventBus()
    synapse = Synapse(db_path="diagnostic_memory.db") # Connect to same DB as Senses
    
    # 2. Wire Monitor to Bus
    async def monitor_bus(msg):
        if msg.topic == "SYSTEM_LOG":
            level = msg.payload.get("level", "INFO")
            message = msg.payload.get("message", "")
            
            if level == "ERROR":
                print(f"{Fore.RED}[BRAIN ERROR] {message}{Style.RESET_ALL}")
            elif "Analyzing" in message:
                print(f"\n{Fore.CYAN}--- {message} ---{Style.RESET_ALL}")
            else:
                print(f"{Fore.WHITE}[BRAIN] {message}{Style.RESET_ALL}")
                
        elif msg.topic == "EXECUTION_READY":
            ticker = msg.payload.get("ticker", "N/A")
            ev = msg.payload.get("ev", 0)
            print(f"\n{Fore.GREEN}🎯 EXECUTION SIGNAL GENERATED!{Style.RESET_ALL}")
            print(f"{Fore.GREEN}Target: {ticker} | EV Score: {ev:.4f}{Style.RESET_ALL}")
            
        elif msg.topic == "SIM_RESULT":
            ticker = msg.payload.get("ticker")
            win_rate = msg.payload.get("win_rate", 0)
            veto = msg.payload.get("veto", False)
            status = f"{Fore.RED}VETOED" if veto else f"{Fore.GREEN}APPROVED"
            print(f"{Fore.YELLOW}[SIM] {ticker}: Win Rate {win_rate*100:.1f}% -> {status}{Style.RESET_ALL}")

    await bus.subscribe("SYSTEM_LOG", monitor_bus)
    await bus.subscribe("EXECUTION_READY", monitor_bus)
    await bus.subscribe("SIM_RESULT", monitor_bus)

    # 3. Initialize Agent
    print("Initializing BrainAgent...")
    brain = BrainAgent(3, bus, synapse=synapse)
    await brain.setup()

    # 4. Processing Loop
    print(f"{Fore.YELLOW}Awaiting opportunities in Synapse...{Style.RESET_ALL}")
    
    try:
        while True:
            # Check for data
            size = await synapse.opportunities.size()
            if size > 0:
                print(f"\n[SYNAPSE] Found {size} pending opportunities.")
                # Trigger process flow
                await bus.publish("OPPORTUNITIES_READY", {"count": size}, "DIAGNOSTIC")
            
            await asyncio.sleep(5) # Slow tick for diagnostics
            
    except KeyboardInterrupt:
        print(f"\n{Fore.RED}Stopping Brain Diagnostic...{Style.RESET_ALL}")
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
