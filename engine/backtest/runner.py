"""Getting settled markets in, and a backtest out.

This container cannot reach api.kalshi.co, so fetching is deliberately separate
from scoring: the fetch runs wherever the network is, writes a file, and the
scorer runs anywhere over that file. That split is also what makes a backtest
reproducible -- the same file scores the same way next month.
"""

import csv
import json
from pathlib import Path

from .scorer import BacktestResult, score_predictions


def load_settled_markets(path: str | Path) -> list[dict]:
    """Read settled markets from CSV or JSON.

    Expected fields per row:

        ticker          identifier, for your reference
        probability     the engine's estimate, 0-1
        price           the YES price it could have traded at, 0-1
        settled_yes     1 / 0 / true / false -- what actually happened
        confidence      optional, 0-1

    Raises on a malformed file rather than silently scoring fewer rows: a
    backtest quietly missing half its data is worse than no backtest.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"No such backtest file: {path}")

    if path.suffix.lower() == ".json":
        rows = json.loads(path.read_text())
        if not isinstance(rows, list):
            raise ValueError("JSON backtest data must be a list of row objects")
    else:
        with path.open(newline="") as handle:
            rows = list(csv.DictReader(handle))

    return [_coerce(row, index) for index, row in enumerate(rows, start=1)]


def _coerce(row: dict, index: int) -> dict:
    """Numbers out of a CSV arrive as strings. Fail loudly on anything unusable."""
    out = {"ticker": row.get("ticker") or f"row-{index}"}

    for field in ("probability", "price", "confidence"):
        value = row.get(field)
        if value in (None, ""):
            out[field] = None
            continue
        try:
            out[field] = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Row {index} ({out['ticker']}): {field}={value!r} is not a number"
            ) from exc

    settled = row.get("settled_yes")
    if settled in (None, ""):
        out["settled_yes"] = None
    elif isinstance(settled, bool):
        out["settled_yes"] = settled
    else:
        text = str(settled).strip().lower()
        if text in ("1", "true", "yes", "y"):
            out["settled_yes"] = True
        elif text in ("0", "false", "no", "n"):
            out["settled_yes"] = False
        else:
            raise ValueError(
                f"Row {index} ({out['ticker']}): settled_yes={settled!r} is not a yes/no outcome"
            )

    return out


def run_backtest(path: str | Path, **kwargs) -> BacktestResult:
    """Load settled markets from `path` and score the engine against them."""
    return score_predictions(load_settled_markets(path), **kwargs)


def format_report(result: BacktestResult) -> str:
    """A report you can read at a glance and act on."""
    lines = [result.summary(), ""]

    if result.calibration:
        lines.append("Calibration -- what it said, against what happened:")
        for bucket in result.calibration:
            lines.append(
                f"  {bucket['bucket']:>9}  n={bucket['n']:4d}  "
                f"said {bucket['predicted']:.0%}  happened {bucket['actual']:.0%}  "
                f"gap {bucket['gap']:+.2f}"
            )
        lines.append("")

    if result.brier is not None:
        skilled = result.brier < 0.25
        verdict = (
            "better than always guessing 50%" if skilled else "NO BETTER than always guessing 50%"
        )
        lines.append(f"Brier {result.brier:.4f} -- {verdict}.")

        # A positive return on a sample is not evidence of edge. Buying cheap
        # long shots pays enormously on the few that land, so pure noise can
        # post a profit over hundreds of markets. Calibration is what
        # distinguishes a forecaster from a lottery ticket, so say so loudly
        # when the two disagree.
        if not skilled and (result.return_per_trade or 0) > 0:
            lines.append("")
            lines.append(
                "WARNING: this sample made money while being no better than a coin "
                "flip. That happens when cheap long shots land, and it is not "
                "evidence of edge. Trust the calibration, not the return."
            )

    return "\n".join(lines)
