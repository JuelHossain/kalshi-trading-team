"""Test SSE connection and trigger cycle to see events"""
import asyncio
import aiohttp
import json

async def test_sse():
    """Test SSE connection"""
    async with aiohttp.ClientSession() as session:
        # First trigger a cycle
        print("Triggering cycle...")
        async with session.post(
            "http://localhost:3002/api/trigger",
            json={"isPaperTrading": True},
            headers={"Content-Type": "application/json"}
        ) as resp:
            print(f"Trigger response: {await resp.text()}")

        print("\nConnecting to SSE stream...")
        async with session.get("http://localhost:3002/api/stream") as resp:
            print(f"SSE Response status: {resp.status}")
            print("Reading events (5 seconds)...")
            print("-" * 50)

            # Read events for 5 seconds
            start = asyncio.get_event_loop().time()
            events_received = 0

            async for line in resp.content:
                current = asyncio.get_event_loop().time()
                if current - start > 5:
                    break

                line_str = line.decode().strip()
                if line_str:
                    if line_str.startswith("data: "):
                        data = line_str[6:]
                        try:
                            event = json.loads(data)
                            events_received += 1
                            print(f"Event {events_received}: {json.dumps(event, indent=2)[:200]}")
                        except json.JSONDecodeError:
                            print(f"Raw data: {data}")

            print(f"\nTotal events received: {events_received}")

if __name__ == "__main__":
    asyncio.run(test_sse())
