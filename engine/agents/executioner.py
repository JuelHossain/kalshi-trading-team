import os
import json
import asyncio
import time
import base64
from typing import Dict, Any
from agents.base import BaseAgent
from core.bus import EventBus
from colorama import Fore, Style

try:
    import aiohttp
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives import serialization
except ImportError:
    pass

class ExecutionerAgent(BaseAgent):
    """
    Agent 8: The Executioner
    Role: Silent Sniper (Limit Orders Only).
    Executes trades approved by the Auditor and the Vault.
    """
    
    def __init__(self, agent_id: int, bus: EventBus):
        super().__init__("EXECUTIONER", agent_id, bus)
        self.private_key = None
        self.key_id = None
        self.base_url = "https://trading-api.kalshi.com/trade-api/v2"

    async def start(self):
        # Load Credentials (mirrors Scout)
        self.key_id = os.getenv("KALSHI_PROD_KEY_ID") or os.getenv("KALSHI_DEMO_KEY_ID")
        private_key_pem = os.getenv("KALSHI_PROD_PRIVATE_KEY") or os.getenv("KALSHI_DEMO_PRIVATE_KEY")
        
        if os.getenv("KALSHI_PROD_KEY_ID"):
            self.base_url = "https://trading-api.kalshi.com/trade-api/v2"
        else:
            self.base_url = "https://demo-api.kalshi.com/trade-api/v2"

        if private_key_pem:
            try:
                if "\\n" in private_key_pem:
                    private_key_pem = private_key_pem.replace("\\n", "\n")
                self.private_key = serialization.load_pem_private_key(
                    private_key_pem.encode(), password=None
                )
            except Exception as e:
                await self.log(f"Crypto Init Failed: {e}")

        await self.log(f"Sniper Online. Ready to execute on {self.base_url}")
        
        # Subscribe to final audit decisions
        await self.bus.subscribe("AUDIT_DECISION", self.handle_execution_request)

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

    async def handle_execution_request(self, message):
        data = message.payload
        ticker = data.get('ticker')
        approved = data.get('approved', False)
        
        if not approved:
            return # Ignore rejected trades

        await self.log(f"SNIPING: Initiating execution protocol for {ticker}...")
        
        # Parameters for Snipe
        # In a real run, these would be calculated based on Bankroll/Risk
        order_params = {
            "action": "buy",
            "count": 1,
            "side": "yes",
            "ticker": ticker,
            "type": "limit", # PROTOCOL: Silent Sniper
            "yes_price": 50, # Mock price
            "client_order_id": f"ghost_{int(time.time())}"
        }
        
        result = await self.submit_order(order_params)
        
        if result:
            await self.log(f"{Fore.GREEN}SNIPE SUCCESS: {ticker} executed.{Style.RESET_ALL}")
            await self.bus.publish("TRADE_EXECUTED", {"ticker": ticker, "order": order_params}, self.name)
        else:
            await self.log(f"{Fore.RED}SNIPE FAILED: API rejected order for {ticker}.{Style.RESET_ALL}")

    async def submit_order(self, params: Dict) -> bool:
        path = "/portfolio/orders"
        headers = self.get_headers("POST", path)
        url = f"{self.base_url}{path}"
        
        if not self.private_key or "mock" in self.key_id:
             await self.log("MOCK SNIPE: Order payload generated (Dry Run).")
             return True # Mock success in dry runs

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, headers=headers, json=params) as resp:
                    if resp.status == 201 or resp.status == 200:
                        return True
                    else:
                        error_body = await resp.text()
                        await self.log(f"Kalshi order error {resp.status}: {error_body}")
                        return False
            except Exception as e:
                await self.log(f"Order Connection Error: {e}")
                return False
