"""Check this machine is configured to talk to Kalshi, without printing secrets.

    python engine/scripts/preflight.py            # check configuration only
    python engine/scripts/preflight.py --connect  # also attempt a real handshake

Reports what is present, what is missing and what is wrong. It never prints a
credential: a secret that reaches a terminal reaches the scrollback, the shell
history and any screenshot of either. Lengths and PEM validity are enough to
tell a missing key from a malformed one, which is the only question worth
asking here.
"""

import argparse
import asyncio
import hashlib
import os
import sys
from pathlib import Path

ENGINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ENGINE))

# The password that was committed to this repository. Stored as a digest so
# checking for it does not put the value back in the source tree.
LEAKED_AUTH_PASSWORD_SHA256 = "ab74c38e108520a4a8d2ad754ab7e5f1ae347c3f61888d9023b78ef0214e345b"

OK, WARN, BAD = "  ok  ", " warn ", " FAIL "


def _load_env() -> Path | None:
    for candidate in (ENGINE / ".env", ENGINE.parent / ".env"):
        if candidate.exists():
            try:
                from dotenv import load_dotenv

                load_dotenv(candidate)
            except ImportError:
                for line in candidate.read_text().splitlines():
                    if "=" in line and not line.strip().startswith("#"):
                        k, _, v = line.partition("=")
                        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
            return candidate
    return None


def _row(status: str, name: str, detail: str = "") -> bool:
    print(f"[{status}] {name:<26} {detail}")
    return status == OK


def main() -> int:
    """Check this machine's configuration and print a readiness report; exit 1 on any blocker."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--connect", action="store_true", help="attempt a real Kalshi handshake")
    args = parser.parse_args()

    env_file = _load_env()
    print(f"\nenv file: {env_file or 'NONE FOUND — create engine/.env'}\n")

    failures = 0

    # --- which venue
    env = os.getenv("KALSHI_ENV", "demo").strip().lower()
    if env == "demo":
        _row(OK, "KALSHI_ENV", "demo — play money")
    elif env == "prod":
        _row(WARN, "KALSHI_ENV", "prod — REAL MONEY")
    else:
        failures += 1
        _row(BAD, "KALSHI_ENV", f"{env!r} is not 'demo' or 'prod'")
        return _summary(failures)

    prefix = "KALSHI_DEMO" if env == "demo" else "KALSHI_PROD"

    # --- credentials for that venue
    key_id = os.getenv(f"{prefix}_KEY_ID")
    if key_id:
        _row(OK, f"{prefix}_KEY_ID", f"set ({len(key_id)} chars)")
    else:
        failures += 1
        _row(BAD, f"{prefix}_KEY_ID", "missing")

    pem = os.getenv(f"{prefix}_PRIVATE_KEY")
    if not pem:
        failures += 1
        _row(BAD, f"{prefix}_PRIVATE_KEY", "missing")
    else:
        try:
            from cryptography.hazmat.primitives import serialization

            body = pem.replace("\\n", "\n").strip().strip('"')
            serialization.load_pem_private_key(body.encode(), password=None)
            _row(OK, f"{prefix}_PRIVATE_KEY", "valid PEM, parsed")
        except Exception as e:
            failures += 1
            _row(BAD, f"{prefix}_PRIVATE_KEY", f"will not parse: {str(e)[:60]}")

    # --- engine's own secrets
    password = os.getenv("AUTH_PASSWORD")
    if not password:
        failures += 1
        _row(BAD, "AUTH_PASSWORD", "missing — the engine refuses to start")
    elif hashlib.sha256(password.encode()).hexdigest() == LEAKED_AUTH_PASSWORD_SHA256:
        failures += 1
        _row(BAD, "AUTH_PASSWORD", "this is the password that leaked. ROTATE IT.")
    elif len(password) < 12:
        _row(WARN, "AUTH_PASSWORD", f"set, but short ({len(password)} chars)")
    else:
        _row(OK, "AUTH_PASSWORD", f"set ({len(password)} chars)")

    for name, needed_for in (
        ("GHOST_API_KEY", "engine <-> dashboard auth"),
        ("GEMINI_API_KEY", "the Brain's probability estimates"),
    ):
        if os.getenv(name):
            _row(OK, name, "set")
        else:
            failures += 1
            _row(BAD, name, f"missing — needed for {needed_for}")

    # --- trading mode
    paper = os.getenv("IS_PAPER_TRADING", "").strip().lower() in ("true", "1", "yes")
    if paper:
        _row(OK, "IS_PAPER_TRADING", "true — orders are simulated")
    else:
        _row(WARN, "IS_PAPER_TRADING", "not set — the dashboard decides per cycle")

    if args.connect:
        failures += _handshake(env)

    return _summary(failures)


def _handshake(env: str) -> int:
    print(f"\nconnecting to Kalshi ({env})...")
    try:
        from core.network import KalshiClient

        async def go():
            """Run the signed handshake against Kalshi and report the outcome."""
            client = KalshiClient()
            balance = await client.get_balance()
            await client.close()
            return client.base_url, balance

        url, balance = asyncio.run(go())
        _row(OK, "handshake", f"{url}")
        _row(OK, "balance", f"${balance / 100:,.2f}")
        return 0
    except Exception as e:
        _row(BAD, "handshake", str(e)[:120])
        return 1


def _summary(failures: int) -> int:
    if failures:
        print(f"\n{failures} problem(s) to fix before the engine can run.\n")
        return 1
    print("\nReady. Nothing above blocks a first connection.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
