import asyncio
import aiohttp
import time
import base64
import os
import json
from typing import Dict, Any, Optional, List
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization
from colorama import Fore, Style


class KalshiClient:
    """
    Centralized, Self-Healing Kalshi API Client.
    Handles Authentication, Connection Pooling, and Exponential Backoff.
    """

    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None
        self.private_key = None

        # Use Demo API by default (paper trading)
        is_prod = os.getenv("IS_PRODUCTION") == "true"
        
        if is_prod:
            self.key_id = os.getenv("KALSHI_PROD_KEY_ID")
            self.base_url = "https://api.kalshi.co/trade-api/v2"
            pk_pem = os.getenv("KALSHI_PROD_PRIVATE_KEY")
        else:
            # Demo/Sandbox mode (default)
            self.key_id = os.getenv("KALSHI_DEMO_KEY_ID")
            self.base_url = "https://demo-api.kalshi.co/trade-api/v2"
            pk_pem = os.getenv("KALSHI_DEMO_PRIVATE_KEY")
        
        if pk_pem:
            try:
                if "\\n" in pk_pem:
                    pk_pem = pk_pem.replace("\\n", "\n")
                if pk_pem.startswith('"') and pk_pem.endswith('"'):
                    pk_pem = pk_pem[1:-1]

                self.private_key = serialization.load_pem_private_key(
                    pk_pem.encode(), password=None
                )
            except Exception as e:
                print(f"{Fore.RED}[NETWORK] Crypto Init Failed: {e}{Style.RESET_ALL}")

    async def get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=5.0), connector=aiohttp.TCPConnector(limit=10)
            )
        return self._session

    def _get_headers(self, method: str, path: str, body: str = "") -> Dict[str, str]:
        if not self.private_key:
            return {"Content-Type": "application/json"}

        timestamp = str(int(time.time() * 1000))
        msg = f"{timestamp}{method}{path}{body}"
        print(f"[NETWORK] Signing message: {msg}")

        signature_bytes = self.private_key.sign(
            msg.encode(),
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256(),
        )
        signature = base64.b64encode(signature_bytes).decode()
        print(f"[NETWORK] Generated signature: {signature}")

        return {
            "KALSHI-ACCESS-KEY": self.key_id,
            "KALSHI-ACCESS-SIGNATURE": signature,
            "KALSHI-ACCESS-TIMESTAMP": timestamp,
            "Content-Type": "application/json",
        }

    async def request(
        self,
        method: str,
        path: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        retries: int = 3,
    ) -> Optional[Dict]:
        """
        Execute an HTTP request with exponential backoff for 429/50x errors.
        """
        session = await self.get_session()
        url = f"{self.base_url}{path}"

        body_str = json.dumps(json_data) if json_data else ""
        for attempt in range(retries):
            headers = self._get_headers(method, path, body_str)
            try:
                async with session.request(
                    method, url, headers=headers, params=params, json=json_data
                ) as resp:
                    print(f"[NETWORK] API Response: {resp.status} for {method} {path}")
                    if resp.status == 200:
                        data = await resp.json()
                        print(f"[NETWORK] Response data keys: {list(data.keys()) if isinstance(data, dict) else 'not dict'}")
                        return data

                    if resp.status == 429 or 500 <= resp.status <= 504:
                        error_text = await resp.text()
                        print(f"[NETWORK] Error response: {error_text}")
                        wait = (2**attempt) + (time.time() % 1)  # Exponential backoff + jitter
                        print(
                            f"{Fore.YELLOW}[NETWORK] Attempt {attempt+1} failed ({resp.status}). Retrying in {wait:.2f}s...{Style.RESET_ALL}"
                        )
                        await asyncio.sleep(wait)
                        continue

                    error_text = await resp.text()
                    print(
                        f"{Fore.RED}[NETWORK] API Error {resp.status}: {error_text}{Style.RESET_ALL}"
                    )
                    return None

            except Exception as e:
                print(f"{Fore.RED}[NETWORK] Connection Error: {e}{Style.RESET_ALL}")
                if attempt < retries - 1:
                    await asyncio.sleep(1)
                    continue
                return None

        return None

    async def get_active_markets(self, limit: int = 100, status: str = "open") -> List[Dict]:
        path = "/markets"
        params = {"limit": limit, "status": status}
        res = await self.request("GET", path, params=params)
        return res.get("markets", []) if res else []

    async def get_orderbook(self, ticker: str) -> Optional[Dict]:
        path = f"/markets/{ticker}/orderbook"
        return await self.request("GET", path)

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()


# Singleton instance
kalshi_client = KalshiClient()
