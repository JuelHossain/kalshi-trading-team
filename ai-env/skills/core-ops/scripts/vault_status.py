#!/usr/bin/env python3
"""
Quick vault state check without starting full HUD.
Shows balance, positions, and risk metrics.
"""

import argparse
import asyncio
import sys
import os
import json
from urllib.request import urlopen, Request
from urllib.error import URLError

VAULT_API_URL = "http://localhost:3002/api/vault"
POSITIONS_API_URL = "http://localhost:3002/api/positions"
ENGINE_HEALTH_URL = "http://localhost:3002/health"


def fetch_json(url: str, timeout: int = 2) -> dict | None:
    """Fetch JSON from API endpoint."""
    try:
        req = Request(url, headers={'Accept': 'application/json'})
        with urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                return json.loads(response.read().decode())
    except URLError as e:
        return None
    except Exception as e:
        return None
    return None


def format_currency(amount: float) -> str:
    """Format amount as currency."""
    return f"${amount:,.2f}"


def format_percentage(value: float) -> str:
    """Format value as percentage."""
    return f"{value*100:.2f}%"


def check_engine_status() -> tuple[bool, dict]:
    """Check if engine is running and get basic info."""
    data = fetch_json(ENGINE_HEALTH_URL)
    if data:
        return True, data
    return False, {}


def get_vault_status() -> dict | None:
    """Get vault state from engine."""
    return fetch_json(VAULT_API_URL)


def get_positions() -> list | None:
    """Get current positions."""
    data = fetch_json(POSITIONS_API_URL)
    if data and isinstance(data, list):
        return data
    return []


def display_vault_status(vault: dict, positions: list):
    """Display formatted vault status."""

    print(f"\n{'='*60}")
    print(f"VAULT STATUS")
    print(f"{'='*60}\n")

    # Balance Information
    print("BALANCE:")
    print(f"  Total Balance:    {format_currency(vault.get('balance', 0))}")
    print(f"  Available:        {format_currency(vault.get('available', 0))}")
    print(f"  Deployed:         {format_currency(vault.get('deployed', 0))}")
    print(f"  P&L (All Time):   {format_currency(vault.get('pnl', 0))}")

    # Risk Metrics
    print("\nRISK METRICS:")
    print(f"  Max Position:     {format_currency(vault.get('max_position_size', 0))}")
    print(f"  Risk Limit:       {format_currency(vault.get('risk_limit', 0))}")
    print(f"  Utilization:      {format_percentage(vault.get('utilization', 0))}")

    # Positions Summary
    if positions:
        print(f"\nPOSITIONS ({len(positions)} active):")
        print(f"  {'Ticker':<20} {'Side':<6} {'Quantity':>10} {'Avg Price':>10} {'P&L':>12}")
        print(f"  {'-'*64}")

        total_pnl = 0
        for pos in positions:
            ticker = pos.get('ticker', 'UNKNOWN')[:20]
            side = pos.get('side', 'YES')[:6]
            qty = pos.get('quantity', 0)
            avg_price = pos.get('avg_price', 0)
            pnl = pos.get('unrealized_pnl', 0)
            total_pnl += pnl

            print(f"  {ticker:<20} {side:<6} {qty:>10} {avg_price:>10.2f} {pnl:>12.2f}")

        print(f"  {'-'*64}")
        print(f"  {'UNREALIZED P&L':>43} {total_pnl:>12.2f}")
    else:
        print("\nPOSITIONS: None")

    print(f"\n{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Quick vault state check without full HUD",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Show full status
  %(prog)s --json                    # Output as JSON
  %(prog)s --balance-only            # Show only balance
  %(prog)s --positions               # Show only positions
        """
    )

    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--balance-only", action="store_true", help="Show only balance information")
    parser.add_argument("--positions", action="store_true", help="Show only positions")

    args = parser.parse_args()

    # Check engine status
    engine_running, engine_info = check_engine_status()

    if not engine_running:
        print("Error: Engine is not running on port 3002", file=sys.stderr)
        print("Start the engine with: python engine/main.py", file=sys.stderr)
        sys.exit(1)

    # Fetch data
    vault = get_vault_status()
    positions_data = get_positions()

    if vault is None:
        print("Error: Could not fetch vault status", file=sys.stderr)
        sys.exit(2)

    positions = positions_data or []

    # Output based on flags
    if args.json:
        output = {
            "vault": vault,
            "positions": positions,
            "position_count": len(positions)
        }
        print(json.dumps(output, indent=2))
    elif args.balance_only:
        print(f"\nBalance: {format_currency(vault.get('balance', 0))}")
        print(f"Available: {format_currency(vault.get('available', 0))}")
        print(f"Deployed: {format_currency(vault.get('deployed', 0))}")
        print(f"P&L: {format_currency(vault.get('pnl', 0))}\n")
    elif args.positions:
        if positions:
            print(f"\n{len(positions)} active positions:")
            for pos in positions:
                print(f"  - {pos.get('ticker', 'UNKNOWN')}: {pos.get('quantity', 0)} @ {pos.get('avg_price', 0):.2f}")
            print()
        else:
            print("\nNo active positions\n")
    else:
        display_vault_status(vault, positions)

    sys.exit(0)


if __name__ == "__main__":
    main()
