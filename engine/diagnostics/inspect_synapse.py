import asyncio
import sys
import os

# Ensure engine path is in sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.synapse import Synapse

async def main():
    synapse = Synapse(db_path="diagnostic_memory.db")
    
    opp_size = await synapse.opportunities.size()
    exec_size = await synapse.executions.size()
    
    print(f"--- Synapse Status ---")
    print(f"Pending Opportunities: {opp_size}")
    print(f"Pending Executions:    {exec_size}")
    
    if opp_size > 0:
        print(f"\nLast Opportunity in Queue:")
        # We don't want to pop, just peek? We don't have peek in Synapse yet.
        # Let's pop and push it back to peek.
        item = await synapse.opportunities.pop()
        if item:
            print(f"- {item.ticker}")
            await synapse.opportunities.push(item)

if __name__ == "__main__":
    asyncio.run(main())
