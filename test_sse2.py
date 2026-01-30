"""Test SSE connection - connect first, then trigger cycle"""
import asyncio
import aiohttp
import json

async def test_sse():
    """Test SSE connection"""
    async with aiohttp.ClientSession() as session:
        print("Connecting to SSE stream...")
        async with session.get("http://localhost:3002/api/stream") as resp:
            print(f"SSE Response status: {resp.status}")
            print("Waiting for events...")

            # Read events
            events_received = 0
            start = asyncio.get_event_loop().time()

            # Wait 1 second for connection to establish
            await asyncio.sleep(1)

            # Now trigger a cycle
            print("Triggering cycle...")
            async with session.post(
                "http://localhost:3002/api/trigger",
                json={"isPaperTrading": True},
                headers={"Content-Type": "application/json"}
            ) as trigger_resp:
                print(f"Trigger response: {await trigger_resp.text()}")

            print("Reading events (10 seconds)...")
            print("-" * 50)

            async for line in resp.content:
                current = asyncio.get_event_loop().time()
                if current - start > 10:
                    print("Timeout reached")
                    break

                try:
                    line_str = line.decode().strip()
                    if line_str:
                        if line_str.startswith("data: "):
                            data = line_str[6:]
                            try:
                                event = json.loads(data)
                                events_received += 1
                                print(f"\nEvent {events_received}:")
                                print(json.dumps(event, indent=2))
                            except json.JSONDecodeError:
                                print(f"Raw data: {data}")
                except Exception as e:
                    print(f"Error reading line: {e}")

            print(f"\nTotal events received: {events_received}")

if __name__ == "__main__":
    asyncio.run(test_sse())
