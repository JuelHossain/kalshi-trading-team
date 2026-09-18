"""Attach realised outcomes to stored predictions.

Polls the public Kalshi market endpoint for every prediction whose close
time has passed and whose outcome is still unknown, then writes back
1 for YES and 0 for NO. Safe to run repeatedly; already-settled rows are
skipped.

Usage:
    python research/settle.py
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime
from typing import Any

import aiohttp

from research import store
from research.predict import DEFAULT_API_BASE

_SETTLED_STATUSES = {"settled", "finalized", "determined"}


async def fetch_market(
    session: aiohttp.ClientSession, api_base: str, ticker: str
) -> dict[str, Any] | None:
    """Fetch a single market record, or None if the lookup fails."""
    try:
        async with session.get(f"{api_base}/markets/{ticker}") as resp:
            if resp.status != 200:
                return None
            payload = await resp.json()
    except (aiohttp.ClientError, TimeoutError):
        return None
    return payload.get("market")


def outcome_from(market: dict[str, Any]) -> int | None:
    """Map a settled market to 1 (yes), 0 (no), or None if unresolved.

    A market can be past its close time but not yet determined, so status is
    checked before trusting the result field.
    """
    status = str(market.get("status", "")).lower()
    result = str(market.get("result", "")).lower()
    if status not in _SETTLED_STATUSES and not result:
        return None
    if result == "yes":
        return 1
    if result == "no":
        return 0
    return None


async def run(args: argparse.Namespace) -> None:
    """Resolve every pending prediction whose market has closed."""
    now = datetime.now(UTC)
    timeout = aiohttp.ClientTimeout(total=30)

    with store.connect() as conn:
        pending = store.pending_settlement(conn, now.isoformat())
        if not pending:
            print("Nothing awaiting settlement.")
            print(f"Totals by variant: {store.counts(conn)}")
            return

        print(f"{len(pending)} predictions past close, checking outcomes...")
        resolved = 0
        unresolved = 0

        async with aiohttp.ClientSession(timeout=timeout) as session:
            for row in pending:
                market = await fetch_market(session, args.api_base, row["ticker"])
                if market is None:
                    unresolved += 1
                    continue

                outcome = outcome_from(market)
                if outcome is None:
                    unresolved += 1
                else:
                    store.record_outcome(conn, row["id"], outcome, now.isoformat())
                    resolved += 1
                    label = "YES" if outcome else "NO"
                    print(f"  {row['ticker']:<28} settled {label}")
                await asyncio.sleep(args.delay)

        print(f"\nResolved {resolved}, still pending {unresolved}")
        print(f"Totals by variant: {store.counts(conn)}")


def main() -> None:
    """Entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--delay", type=float, default=0.5)
    parser.add_argument("--api-base", default=DEFAULT_API_BASE)
    asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    main()
