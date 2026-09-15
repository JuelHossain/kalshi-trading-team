"""Collect model probability estimates for open Kalshi markets.

Places no orders and needs no Kalshi credentials — market data is read from
the public endpoints. Each run samples eligible markets, asks the model for
a probability, and stores the estimate alongside the market's own implied
probability so the two can be scored against each other once the market
settles.

Two prompt variants:
    blind    -- the model never sees the market price (default)
    anchored -- the model is shown the price, mirroring the prompt in
                engine/agents/brain/agent.py

Run both to separate genuine information from price anchoring.

Usage:
    python -m research.predict --count 25
    python -m research.predict --count 25 --variant anchored
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import aiohttp

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from research import store  # noqa: E402

DEFAULT_API_BASE = os.getenv(
    "KALSHI_API_BASE", "https://api.elections.kalshi.com/trade-api/v2"
)
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Multi-variate "cross category" combo shards. Kalshi lists these in
# enormous numbers -- they swamped the first 8,000 markets returned during
# development -- and they are unquoted, zero-volume, and have machine
# generated titles. Excluded by prefix rather than by the volume filter so
# they never consume a page of results.
MVE_PREFIX = "KXMVE"

# OpenRouter's free tier churns; the list inherited from engine/core/ai_client.py
# was entirely 404 by the time this was written. Verified working against
# GET /api/v1/models, first entry is the primary and the rest are fallbacks.
#
# Fallbacks change which model produced a row, which weakens the study, so
# model_name is stored per prediction and the analysis can stratify on it.
# If the primary starts 404-ing, re-check the free list before editing.
OPENROUTER_MODELS = [
    "nvidia/nemotron-3-super-120b-a12b:free",
    "nvidia/nemotron-3.5-lightning:free",
]

_PAGE_LIMIT = 1000
_MAX_PAGES = 5


def _load_env() -> None:
    """Best-effort load of engine/.env so a local key is picked up.

    In CI the key arrives through the environment instead.
    """
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(Path(__file__).resolve().parent.parent / "engine" / ".env")


def _money(value: object) -> float:
    """Parse a Kalshi decimal string. Prices are dollars, so already 0-1."""
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0


def _cents(value: object) -> int | None:
    """Convert a Kalshi dollar string to whole cents for storage."""
    parsed = _money(value)
    return round(parsed * 100) if 0 < parsed < 1 else None


async def fetch_markets(
    session: aiohttp.ClientSession, api_base: str, *, max_days: int
) -> list[dict[str, Any]]:
    """Fetch open markets closing within ``max_days``.

    The close window is applied server side. Without it the response is
    almost entirely combo shards and real markets are never reached.
    """
    now = datetime.now(UTC)
    params_base = {
        "limit": _PAGE_LIMIT,
        "status": "open",
        "min_close_ts": int(now.timestamp()),
        "max_close_ts": int((now + timedelta(days=max_days)).timestamp()),
    }

    collected: list[dict[str, Any]] = []
    cursor: str | None = None

    for _ in range(_MAX_PAGES):
        params = dict(params_base)
        if cursor:
            params["cursor"] = cursor
        async with session.get(f"{api_base}/markets", params=params) as resp:
            if resp.status != 200:
                body = await resp.text()
                msg = f"Kalshi returned {resp.status}: {body[:200]}"
                raise RuntimeError(msg)
            payload = await resp.json()

        page = payload.get("markets", [])
        collected.extend(page)
        cursor = payload.get("cursor")
        if not cursor or not page:
            break

    return collected


def implied_probability(market: dict[str, Any]) -> float | None:
    """Return the market's implied probability of YES, or None if unquoted.

    Uses the bid/ask midpoint when both sides are quoted, since that is the
    fairest single-number summary of where the market sits.
    """
    bid = _money(market.get("yes_bid_dollars"))
    ask = _money(market.get("yes_ask_dollars"))
    if 0 < bid < 1 and 0 < ask < 1:
        return (bid + ask) / 2
    last = _money(market.get("last_price_dollars"))
    return last if 0 < last < 1 else None


def is_eligible(
    market: dict[str, Any],
    *,
    min_volume: float,
    max_spread_cents: int,
) -> bool:
    """Filter to markets that make a usable observation.

    Wide spreads make "the market probability" meaningless and thin volume
    makes it uninformative. The close window is already applied server side.
    """
    if str(market.get("ticker", "")).startswith(MVE_PREFIX):
        return False

    bid = _money(market.get("yes_bid_dollars"))
    ask = _money(market.get("yes_ask_dollars"))
    if not (0 < bid < 1 and 0 < ask < 1):
        return False
    if (ask - bid) * 100 > max_spread_cents:
        return False

    return _money(market.get("volume_fp")) >= min_volume


def build_prompt(market: dict[str, Any], *, anchored: bool) -> str:
    """Build the estimation prompt.

    Args:
        market: Raw Kalshi market record.
        anchored: When True, include the market price, reproducing the
            prompt used by the Brain agent. When False, withhold it so the
            estimate is independent of the price being tested against.
    """
    title = market.get("title") or market.get("ticker", "")
    strike = market.get("yes_sub_title") or ""
    close = market.get("close_time", "unknown")

    price_line = ""
    if anchored:
        prob = implied_probability(market)
        price_line = f"\nCurrent market price: {prob * 100:.1f}%" if prob else ""

    return f"""Estimate the TRUE probability (0.00 to 1.00) that this event resolves YES.

MARKET: {market.get('ticker', '')}
QUESTION: {title}
CONDITION: {strike}
RESOLVES BY: {close}{price_line}

Reason from what you know about the underlying situation. Report a
confidence from 0 to 100 reflecting how much relevant information you
actually have — low confidence is the correct answer when you know little.

Respond with JSON only:
{{"estimated_probability": 0.00, "confidence": 0, "reasoning": "one sentence"}}
"""


def parse_response(text: str) -> tuple[float, float, str] | None:
    """Extract (probability, confidence, reasoning) from a model reply."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group())
        prob = float(data["estimated_probability"])
        conf = float(data.get("confidence", 0)) / 100
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None
    if not 0.0 <= prob <= 1.0:
        return None
    return prob, max(0.0, min(1.0, conf)), str(data.get("reasoning", ""))[:500]


async def ask_model(
    session: aiohttp.ClientSession, api_key: str, prompt: str
) -> tuple[float, float, str, str] | None:
    """Query OpenRouter, trying each free model until one answers usably."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-Title": "Kalshi calibration study",
    }
    for model in OPENROUTER_MODELS:
        body = {"model": model, "messages": [{"role": "user", "content": prompt}]}
        try:
            async with session.post(OPENROUTER_URL, headers=headers, json=body) as resp:
                if resp.status != 200:
                    continue
                payload = await resp.json()
                text = payload["choices"][0]["message"]["content"]
        except (aiohttp.ClientError, KeyError, IndexError, TimeoutError):
            continue
        parsed = parse_response(text)
        if parsed:
            return (*parsed, model)
    return None


async def run(args: argparse.Namespace) -> int:
    """Collect one batch of predictions. Returns the number stored."""
    _load_env()
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        msg = "OPENROUTER_API_KEY is not set (checked environment and engine/.env)"
        raise SystemExit(msg)

    now = datetime.now(UTC)
    anchored = args.variant == "anchored"
    timeout = aiohttp.ClientTimeout(total=120)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        markets = await fetch_markets(session, args.api_base, max_days=args.max_days)
        print(f"Fetched {len(markets)} markets closing within {args.max_days}d")

        with store.connect() as conn:
            seen = store.predicted_tickers(conn, args.variant)
            candidates = [
                m
                for m in markets
                if m.get("ticker") not in seen
                and is_eligible(
                    m,
                    min_volume=args.min_volume,
                    max_spread_cents=args.max_spread,
                )
            ]
            candidates.sort(key=lambda m: _money(m.get("volume_fp")), reverse=True)
            batch = candidates[: args.count]
            print(f"{len(candidates)} eligible, asking about {len(batch)}")

            stored = 0
            for market in batch:
                market_prob = implied_probability(market)
                if market_prob is None:
                    continue

                result = await ask_model(
                    session, api_key, build_prompt(market, anchored=anchored)
                )
                if result is None:
                    print(f"  skip {market['ticker']}: no usable model response")
                    continue
                model_prob, model_conf, reasoning, model_name = result

                inserted = store.record_prediction(
                    conn,
                    {
                        "ticker": market["ticker"],
                        "title": (market.get("title") or "")[:300],
                        "variant": args.variant,
                        "asked_at": now.isoformat(),
                        "close_time": market.get("close_time"),
                        "market_prob": market_prob,
                        "yes_bid": _cents(market.get("yes_bid_dollars")),
                        "yes_ask": _cents(market.get("yes_ask_dollars")),
                        "no_bid": _cents(market.get("no_bid_dollars")),
                        "no_ask": _cents(market.get("no_ask_dollars")),
                        "volume": int(_money(market.get("volume_fp"))),
                        "model_prob": model_prob,
                        "model_conf": model_conf,
                        "model_name": model_name,
                        "reasoning": reasoning,
                    },
                )
                if inserted:
                    stored += 1
                    delta = model_prob - market_prob
                    print(
                        f"  {market['ticker'][:34]:<36} market {market_prob:.2f}  "
                        f"model {model_prob:.2f}  delta {delta:+.2f}  conf {model_conf:.2f}"
                    )
                await asyncio.sleep(args.delay)

            summary = store.counts(conn)
    print(f"\nStored {stored} predictions. Totals by variant: {summary}")
    return stored


def main() -> None:
    """Entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=25, help="predictions per run")
    parser.add_argument("--variant", choices=("blind", "anchored"), default="blind")
    parser.add_argument("--max-days", type=int, default=10, help="max days to close")
    parser.add_argument("--min-volume", type=float, default=200)
    parser.add_argument("--max-spread", type=int, default=8, help="max spread, cents")
    parser.add_argument("--delay", type=float, default=2.0, help="seconds between calls")
    parser.add_argument("--api-base", default=DEFAULT_API_BASE)
    asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    main()
