"""The Kalshi API client.

Signs every request with RSA-PSS, selects the demo or production host from
KALSHI_ENV (demo unless production is asked for by name), retries only on
transient statuses, and funnels every order through place_order -- the one
place that consults trading_mode and returns a simulated fill in paper mode.
Prices and sizes arrive as decimal strings in dollars.
"""

import asyncio
import base64
import os
import time
import uuid

import aiohttp
from core import trading_mode
from core.display import AgentType, log_error, log_warning
from core.lazy import lazy
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


class KalshiAPIError(RuntimeError):
    """Kalshi answered with a non-retryable status.

    Distinct from a connection failure so the retry loop can tell them apart:
    a 401 or 404 is a definitive answer, not a transient fault.
    """


def kalshi_order_body(ticker: str, side: str, price: int, count: int, action: str) -> dict:
    """A Kalshi V2 order (POST /portfolio/events/orders) for the engine's terms.

    The engine speaks in the held side's own price: buy/sell YES or NO at a
    price in cents for that side. Kalshi V2 speaks only YES: "bid" buys YES,
    "ask" sells YES, and price is the YES price in dollars. So buying NO at
    x is an ask at 1 - x, and closing NO is a bid. Per Kalshi's docs,
    checked 2026-09-18. The previous body -- market_id, action, side, type,
    integer price -- matched no Kalshi schema and would have been rejected.

    Orders are immediate-or-cancel: the engine records a placed order as a
    position, so an order must not rest in the book. Sells are reduce_only,
    so a close can never flip or grow a position. client_order_id gives
    each order an identity the exchange can deduplicate on.
    """
    side = side.lower()
    action = action.lower()
    buying_yes = (side == "yes") == (action == "buy")
    yes_price_cents = price if side == "yes" else 100 - price
    body = {
        "ticker": ticker,
        "side": "bid" if buying_yes else "ask",
        "count": f"{int(count)}.00",
        "price": f"{yes_price_cents / 100:.4f}",
        "time_in_force": "immediate_or_cancel",
        "self_trade_prevention_type": "taker_at_cross",
        "client_order_id": str(uuid.uuid4()),
    }
    if action == "sell":
        body["reduce_only"] = True
    return body


class KalshiClient:
    """
    Centralized, Self-Healing Kalshi API Client.
    Handles Authentication, Connection Pooling, and Exponential Backoff.
    """

    # Which Kalshi to talk to. Demo is a separate environment with its own
    # accounts, keys and play money, so it is the only place a first handshake
    # can be made without risking anything.
    ENVIRONMENTS = {
        "demo": ("https://demo-api.kalshi.co/trade-api/v2", "KALSHI_DEMO"),
        # From Kalshi's docs (checked 2026-09-18). The previous host,
        # api.kalshi.co, does not resolve: going live would have failed to
        # connect at all.
        "prod": ("https://external-api.kalshi.com/trade-api/v2", "KALSHI_PROD"),
    }

    def __init__(self):
        self._session: aiohttp.ClientSession | None = None
        self.private_key = None

        # Demo unless production is asked for by name. A previous change removed
        # demo mode entirely and hardcoded the production URL, which left no way
        # to connect to Kalshi at all without risking real money: demo
        # credentials cannot authenticate against the production host. Defaulting
        # to demo means a missing or misspelled setting costs play money.
        self.env = os.getenv("KALSHI_ENV", "demo").strip().lower()
        if self.env not in self.ENVIRONMENTS:
            raise ValueError(
                f"KALSHI_ENV must be one of {sorted(self.ENVIRONMENTS)}, got {self.env!r}."
            )

        self.base_url, prefix = self.ENVIRONMENTS[self.env]

        # Each environment has its own key pair, so they are read separately.
        # Falling back from one to the other would send production credentials
        # to the demo host, or the reverse.
        self.key_id = os.getenv(f"{prefix}_KEY_ID")
        if not self.key_id:
            raise ValueError(
                f"{prefix}_KEY_ID not configured. KALSHI_ENV={self.env} reads "
                f"{prefix}_KEY_ID and {prefix}_PRIVATE_KEY."
            )

        pk_pem = os.getenv(f"{prefix}_PRIVATE_KEY")
        if not pk_pem:
            raise ValueError(
                f"{prefix}_PRIVATE_KEY not configured. KALSHI_ENV={self.env} reads "
                f"{prefix}_KEY_ID and {prefix}_PRIVATE_KEY."
            )

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
                log_error(f"Crypto Init Failed: {e}", AgentType.GATEWAY)

    async def get_session(self) -> aiohttp.ClientSession:
        """Lazily create the shared aiohttp session: 5s total timeout, 10 connections."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=5.0), connector=aiohttp.TCPConnector(limit=10)
            )
        return self._session

    def _get_headers(self, method: str, path: str) -> dict[str, str]:
        if not self.private_key:
            return {"Content-Type": "application/json"}

        # Fix: Signature requires /trade-api/v2 prefix
        full_path = f"/trade-api/v2{path}"
        timestamp = str(int(time.time() * 1000))
        # Kalshi signs timestamp + method + path, and nothing else. The body
        # used to be appended; GETs have none, so reads worked and hid it,
        # while every order POST would have been signed wrong (401).
        msg = f"{timestamp}{method}{full_path}"
        # Note: Signing message logged only in debug mode (removed for security)

        # Fix: Use salt_length=32 (SHA256 digest length) to match Node's RSA_PSS_SALTLEN_DIGEST
        signature_bytes = self.private_key.sign(
            msg.encode(),
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=32),
            hashes.SHA256(),
        )
        signature = base64.b64encode(signature_bytes).decode()
        # print(f"[NETWORK] Generated signature: {signature}")

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
        params: dict | None = None,
        json_data: dict | None = None,
        retries: int = 3,
    ) -> dict | None:
        """
        Execute an HTTP request with exponential backoff for 429/50x errors.
        """
        session = await self.get_session()
        url = f"{self.base_url}{path}"

        # Only reads are safe to repeat. A POST that timed out or got a 5xx
        # may still have been accepted; re-sending it byte for byte could fill
        # an order two or three times against one vault reservation. 429 is
        # always safe: rate-limited means rejected, never processed.
        safe = method.upper() in ("GET", "HEAD")
        for attempt in range(retries):
            # Pass original path here, _get_headers now handles the prefix
            headers = self._get_headers(method, path)
            try:
                async with session.request(
                    method, url, headers=headers, params=params, json=json_data
                ) as resp:
                    # Any 2xx. Kalshi answers a created order with 201, which
                    # used to raise -- a live fill reported as a failure.
                    if 200 <= resp.status < 300:
                        try:
                            return await resp.json(content_type=None) or {}
                        except Exception:
                            return {}

                    if resp.status == 429 or (500 <= resp.status <= 504 and safe):
                        wait = (2**attempt) + (time.time() % 1)
                        log_warning(
                            f"Attempt {attempt+1} failed ({resp.status}). Retrying in {wait:.2f}s...",
                            AgentType.GATEWAY,
                        )
                        await asyncio.sleep(wait)
                        continue

                    error_text = await resp.text()
                    error_msg = f"API Error {resp.status} ({method} {path}): {error_text}"
                    log_error(error_msg, AgentType.GATEWAY)
                    raise KalshiAPIError(error_msg)

            except KalshiAPIError:
                # A definitive answer from Kalshi. Retrying a 4xx three times with
                # sleeps only delayed the same answer and then mislabelled it as a
                # connection error.
                raise
            except Exception as e:
                error_msg = f"Connection Error after {attempt + 1} attempts: {e}"
                log_error(error_msg, AgentType.GATEWAY)
                if safe and attempt < retries - 1:
                    await asyncio.sleep(1)
                    continue
                raise RuntimeError(error_msg) from e

        raise RuntimeError(f"Request failed after {retries} retries: {method} {path}")

    async def get_markets_page(
        self,
        limit: int = 500,
        status: str = "open",
        min_close_ts: int | None = None,
        max_close_ts: int | None = None,
        cursor: str | None = None,
        mve_filter: str | None = None,
    ) -> tuple[list[dict], str | None]:
        """Fetch one page of markets and the cursor for the next.

        Exposed per-page so a caller filtering for tradeable markets can
        stop as soon as it has enough, rather than pulling thousands it will
        discard.

        mve_filter: Kalshi's own filter for multivariate-event (combo)
        markets -- "exclude" or "only". Before this was added, the listing
        inside a close window was dominated by KXMVE combo shards and every
        one of them still had to be downloaded and discarded client-side;
        four consecutive live scans hit the page ceiling (8 pages, 4000
        markets) and returned 3, 2, 1 and then 0 tradeable markets, each
        time "from 4000 scanned" -- the real markets past page 8 were never
        reached at all.
        """
        params: dict = {"limit": limit, "status": status}
        if min_close_ts is not None:
            params["min_close_ts"] = min_close_ts
        if max_close_ts is not None:
            params["max_close_ts"] = max_close_ts
        if cursor:
            params["cursor"] = cursor
        if mve_filter:
            params["mve_filter"] = mve_filter

        res = await self.request("GET", "/markets", params=params)
        if not res or "markets" not in res:
            msg = "Failed to get markets: invalid response format"
            raise RuntimeError(msg)
        return res["markets"], res.get("cursor")

    async def get_active_markets(
        self,
        limit: int = 100,
        status: str = "open",
        min_close_ts: int | None = None,
        max_close_ts: int | None = None,
    ) -> list[dict]:
        """Fetch a single page of markets, optionally bounded by close time."""
        markets, _ = await self.get_markets_page(
            limit=limit,
            status=status,
            min_close_ts=min_close_ts,
            max_close_ts=max_close_ts,
        )
        return markets

    async def get_balance(self) -> int:
        """Fetch current balance. Returns cents."""
        path = "/portfolio/balance"
        res = await self.request("GET", path)
        if res and "balance" in res:
            return int(res["balance"])
        raise RuntimeError("Failed to get balance: invalid response format")

    async def get_orderbook(self, ticker: str) -> dict | None:
        """GET /markets/{ticker}/orderbook. hand.execution.parse_orderbook knows the shape."""
        path = f"/markets/{ticker}/orderbook"
        return await self.request("GET", path)

    async def get_market(self, ticker: str) -> dict | None:
        """GET /markets/{ticker}: a single market's current status and result.

        Nothing called this before, so nothing could ever ask Kalshi whether a
        held market had settled. `core.ledger.outcome_from_market` reads the
        "status" and "result" fields of what this returns.
        """
        res = await self.request("GET", f"/markets/{ticker}")
        return (res or {}).get("market")

    async def place_order(
        self,
        ticker: str,
        side: str,
        type: str,
        price: int,
        count: int,
        action: str = "buy",
        *,
        live: bool | None = None,
    ) -> dict | None:
        """Place an order on Kalshi.

        Args:
            ticker: Market ticker symbol
            side: 'yes' or 'no'
            type: 'limit' or 'market'
            price: Price in cents (1-99)
            count: Number of contracts
            action: 'buy' or 'sell'. The field was previously absent entirely,
                which left the engine unable to express a sell at all -- there
                was no way to exit a position once entered.
            live: Overrides the process-wide trading_mode.is_live() for just
                this call when not None. Ragnarok's own closes pass True here
                so they cannot be flipped to paper fills by a concurrent
                cycle's set_live(False) mid-flatten (main.py disarms live
                before it authorises a cycle); everything else leaves this
                None and defers to the process-wide switch as before.

        Returns:
            Order response dict or None on failure

        In paper mode this returns a simulated fill without contacting Kalshi.
        The check sits here, at the one function entries, exits and Ragnarok all
        funnel through, so no future call site can place a real order by
        forgetting to ask whether it should.

        The halt check sits here for the same reason, and only for buys: a
        halt refuses new exposure, and exits and Ragnarok's closes must still
        go through. Paper buys are refused too, so a paper soak exercises it.
        """
        if action.lower() == "buy" and trading_mode.is_halted():
            reasons = ", ".join(trading_mode.halt_reasons())
            raise RuntimeError(f"Trading halted ({reasons}); refusing new exposure")

        is_live = trading_mode.is_live() if live is None else live
        if not is_live:
            return trading_mode.paper_fill(ticker, side, price, count, action)

        return await self.request(
            "POST",
            "/portfolio/events/orders",
            json_data=kalshi_order_body(ticker, side, price, count, action),
        )

    async def get_positions(self) -> list[dict]:
        """Open positions.

        The client had no way to read these, so the engine could not know what
        it held: it could not avoid doubling into a market, size against
        existing exposure, or close anything.
        """
        res = await self.request("GET", "/portfolio/positions")
        if res and "market_positions" in res:
            return res["market_positions"]
        if res and "positions" in res:
            return res["positions"]
        return []

    async def close_position(
        self, ticker: str, count: int, side: str = "yes", *, live: bool | None = None
    ) -> dict | None:
        """Flatten a holding by selling it back.

        Uses a marketable limit at the extreme tick so an emergency exit is not
        left resting in the book. Getting out matters more than the last cent.

        `live` passes straight through to place_order -- see its docstring.
        """
        # 1c in the held side's own price space is the most marketable sell
        # for either side. NO used to get 99c -- asking 99c for a NO, which
        # would rest, not flatten.
        return await self.place_order(
            ticker=ticker,
            side=side,
            type="limit",
            price=1,
            count=count,
            action="sell",
            live=live,
        )

    async def close(self):
        """Close the shared session. Safe to call more than once."""
        if self._session and not self._session.closed:
            await self._session.close()


# Singleton instance (constructed on first attribute access, not on import)
kalshi_client = lazy(KalshiClient)
