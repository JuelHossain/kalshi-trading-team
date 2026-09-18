"""One scheduled run: settle what closed, then collect new predictions.

Nothing watches stdout when a scheduler invokes this, so every run is
appended to ``research/logs/daily.log`` with a timestamp, and the exit code
reflects whether either stage failed so the scheduler's "last run result"
column stays meaningful.

Settlement runs first so the day's report includes markets that closed
overnight before new rows are added.

Usage:
    python research/daily.py
    python research/daily.py --count 25 --variant blind
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import TextIO

if __package__ in (None, ""):
    # Invoked as a bare script, so the repo root is not on sys.path. A
    # scheduler's working directory cannot be relied on either.
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from research import predict, settle, store  # noqa: E402

LOG_DIR = Path(__file__).parent / "logs"
LOG_FILE = LOG_DIR / "daily.log"
_RULE = "=" * 64


class _Tee:
    """Mirror writes to the console and the log file.

    The collectors already print progress; teeing means a scheduled run
    leaves the same trace on disk without rewriting them to use logging.
    """

    def __init__(self, stream: TextIO, handle: TextIO) -> None:
        self._stream = stream
        self._handle = handle

    def write(self, text: str) -> int:
        self._stream.write(text)
        self._handle.write(text)
        return len(text)

    def flush(self) -> None:
        self._stream.flush()
        self._handle.flush()


def _settle_args(args: argparse.Namespace) -> argparse.Namespace:
    """Build the namespace settle.run expects."""
    return argparse.Namespace(delay=0.5, api_base=args.api_base)


def _predict_args(args: argparse.Namespace) -> argparse.Namespace:
    """Build the namespace predict.run expects."""
    return argparse.Namespace(
        count=args.count,
        variant=args.variant,
        max_days=args.max_days,
        min_volume=args.min_volume,
        max_spread=args.max_spread,
        model=args.model,
        no_grounding=args.no_grounding,
        delay=args.delay,
        api_base=args.api_base,
    )


def _run_stage(name: str, coro_factory) -> bool:
    """Run one stage, reporting failure without aborting the other.

    A Kalshi outage should not cost you the day's predictions, and a model
    outage should not stop outcomes being recorded.
    """
    print(f"\n--- {name} ---")
    try:
        asyncio.run(coro_factory())
    except Exception:  # noqa: BLE001 - a scheduled run must not die silently
        print(f"[{name}] FAILED")
        traceback.print_exc(file=sys.stdout)
        return False
    return True


def main() -> None:
    """Entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=25)
    parser.add_argument("--variant", choices=("blind", "anchored"), default="blind")
    parser.add_argument("--max-days", type=int, default=10)
    parser.add_argument("--min-volume", type=float, default=200)
    parser.add_argument("--max-spread", type=int, default=8)
    parser.add_argument("--model", default=predict.DEFAULT_MODEL)
    parser.add_argument("--no-grounding", action="store_true")
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument("--api-base", default=predict.DEFAULT_API_BASE)
    args = parser.parse_args()

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    started = datetime.now(UTC)

    with LOG_FILE.open("a", encoding="utf-8") as handle:
        original = sys.stdout
        sys.stdout = _Tee(original, handle)
        try:
            print(f"\n{_RULE}")
            print(f"  run started {started.isoformat()}  variant={args.variant}")
            print(_RULE)

            settled_ok = _run_stage(
                "settle", lambda: settle.run(_settle_args(args))
            )
            predict_ok = _run_stage(
                "predict", lambda: predict.run(_predict_args(args))
            )

            with store.connect() as conn:
                totals = store.counts(conn)

            elapsed = (datetime.now(UTC) - started).total_seconds()
            print(f"\n{_RULE}")
            print(f"  finished in {elapsed:.0f}s   totals by variant: {totals}")
            print(f"  settle {'ok' if settled_ok else 'FAILED'}   "
                  f"predict {'ok' if predict_ok else 'FAILED'}")
            print(f"{_RULE}\n")
        finally:
            sys.stdout = original

    raise SystemExit(0 if (settled_ok and predict_ok) else 1)


if __name__ == "__main__":
    main()
