import os
import time
import json
import asyncio
import base64
import datetime
from typing import List, Dict, Any

# Third-party imports
try:
    import aiohttp
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives import serialization
    from dotenv import load_dotenv
    from groq import AsyncGroq
except ImportError:
    # This will guide the user to install dependencies if they try to run it directly
    print("Missing dependencies. Please run: pip install aiohttp cryptography python-dotenv groq")
    exit(1)

# Load .env from the backend directory
load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))

class KalshiHarvester:
    """
    Agent 2 (The Scout) - The Harvester
    
    The Pulse: Asynchronous WebSocket/REST listener for Kalshi v2 /markets.
    Liquidity Filter: open_interest > $2,000 and volume > 100 contracts.
    The Reflex (Groq): Llama 3.1 70B categorization.
    Speed: < 2.5s for full scan.
    """
    
    def __init__(self):
        self.key_id = os.getenv("KALSHI_PROD_KEY_ID")
        private_key_pem = os.getenv("KALSHI_PROD_PRIVATE_KEY")
        
        if not self.key_id or not private_key_pem:
            # Fallback to demo if prod not found
            self.key_id = os.getenv("KALSHI_DEMO_KEY_ID")
            private_key_pem = os.getenv("KALSHI_DEMO_PRIVATE_KEY")
            self.base_url = "https://demo-api.kalshi.com/trade-api/v2"
        else:
            self.base_url = "https://trading-api.kalshi.com/trade-api/v2"

        if private_key_pem:
            if "\\n" in private_key_pem:
                private_key_pem = private_key_pem.replace("\\n", "\n")
            if private_key_pem.startswith('"') and private_key_pem.endswith('"'):
                private_key_pem = private_key_pem[1:-1]
            
            try:
                self.private_key = serialization.load_pem_private_key(
                    private_key_pem.encode(),
                    password=None
                )
            except Exception as e:
                self.private_key = None
        else:
            self.private_key = None

        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.groq_client = AsyncGroq(api_key=self.groq_api_key) if self.groq_api_key else None

    def get_headers(self, method: str, path: str) -> Dict[str, str]:
        if not self.private_key:
            return {"Content-Type": "application/json"}
            
        timestamp = str(int(time.time() * 1000))
        msg = f"{timestamp}{method}{path}"
        
        signature_bytes = self.private_key.sign(
            msg.encode(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        signature = base64.b64encode(signature_bytes).decode()
        
        return {
            "KALSHI-ACCESS-KEY": self.key_id,
            "KALSHI-ACCESS-SIGNATURE": signature,
            "KALSHI-ACCESS-TIMESTAMP": timestamp,
            "Content-Type": "application/json"
        }

    async def fetch_markets(self, limit: int = 1000) -> List[Dict[str, Any]]:
        path = "/markets"
        headers = self.get_headers("GET", path)
        url = f"{self.base_url}{path}?status=active&limit={limit}"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=headers, timeout=1.0) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("markets", [])
                    return []
            except asyncio.TimeoutError:
                return []
            except Exception:
                return []

    def apply_liquidity_filter(self, markets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        filtered = []
        for m in markets:
            oi = m.get("open_interest", 0)
            vol = m.get("volume", 0)
            price = m.get("last_price", 50) 
            dollar_oi = (oi * price) / 100
            
            if dollar_oi > 2000 and vol > 100:
                filtered.append(m)
        return filtered

    async def categorize_market(self, market: Dict[str, Any]) -> str:
        if not self.groq_client: return "Other"
        
        prompt = (
            f"Categorize: {market.get('title', 'N/A')} ({market.get('ticker', 'N/A')})\n"
            "Return EXACTLY one word: Sports, Econ, Weather, or Other."
        )
        
        try:
            chat_completion = await self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.1-70b-versatile",
                temperature=0,
                max_tokens=5
            )
            cat = chat_completion.choices[0].message.content.strip().title()
            return cat if cat in ["Sports", "Econ", "Weather", "Other"] else "Other"
        except Exception:
            return "Other"

    async def listen_to_pulse(self):
        """
        The Pulse: Asynchronous WebSocket listener for real-time market updates.
        """
        ws_url = "wss://trading-api.kalshi.com/trade-api/v2/stream"
        
        # In a real scenario, we would subscribe to 'market_data'
        # For now, this serves as the architectural foundation for real-time liquidity tracking.
        print("[Harvester] Pulse WebSocket listener initialized.")
        # Implementation would follow the Kalshi V2 WS auth protocol
        pass

    async def run_scan(self) -> Dict[str, Any]:
        start_time = time.time()
        
        # REST Fetch for full market view (Initial Pulse)
        markets = await self.fetch_markets()
        
        # Hard-coded Liquidity Filter
        filtered_markets = self.apply_liquidity_filter(markets)
        
        # Groq Llama 3.1 70B Categorization (Parallel Reflex)
        categorization_tasks = [self.categorize_market(m) for m in filtered_markets[:40]]
        categories = await asyncio.gather(*categorization_tasks)
        
        high_prob_tickers = []
        for i, m in enumerate(filtered_markets[:40]):
            high_prob_tickers.append({
                "ticker": m.get("ticker"),
                "category": categories[i],
                "title": m.get("title"),
                "liquidity_score": (m.get("open_interest", 0) * m.get("last_price", 50)) / 100,
                "vol": m.get("volume"),
                "last_price": m.get("last_price")
            })
            
        duration = time.time() - start_time
        
        output = {
            "agent": "The Scout",
            "module": "Harvester",
            "status": "Ready",
            "scan_time_ms": int(duration * 1000),
            "high_probability_tickers": high_prob_tickers
        }
        
        # FINAL OUTPUT SENT TO INTERCEPTOR (via stdout/JSON)
        print(json.dumps(output))
        return output

if __name__ == "__main__":
    harvester = KalshiHarvester()
    asyncio.run(harvester.run_scan())
