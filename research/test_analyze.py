"""Tests for the scoring math.

The collectors are disposable glue, but a bug in here produces a confident
wrong answer to the only question the experiment exists to settle, so the
scoring functions are tested directly.

Run with:
    pytest research/
"""

from __future__ import annotations

import math

from research.analyze import (
    _fee_cents,
    brier,
    calibration,
    log_loss,
    paired_brier,
    simulate,
)


def _row(market: float, model: float, outcome: int, **extra: object) -> dict:
    """Build a minimal prediction row."""
    row = {
        "market_prob": market,
        "model_prob": model,
        "outcome": outcome,
        "model_conf": extra.get("conf", 1.0),
        "yes_ask": extra.get("yes_ask", int(market * 100)),
        "no_ask": extra.get("no_ask", 100 - int(market * 100)),
    }
    return row


class TestBrier:
    def test_perfect_forecast_scores_zero(self):
        assert brier(1.0, 1) == 0.0
        assert brier(0.0, 0) == 0.0

    def test_maximally_wrong_forecast_scores_one(self):
        assert brier(0.0, 1) == 1.0
        assert brier(1.0, 0) == 1.0

    def test_coin_flip_scores_a_quarter(self):
        assert brier(0.5, 1) == 0.25
        assert brier(0.5, 0) == 0.25


class TestLogLoss:
    def test_confident_and_correct_is_near_zero(self):
        assert log_loss(0.99, 1) < 0.02

    def test_confident_and_wrong_is_finite_not_infinite(self):
        """A 0.0 forecast on a YES outcome must not produce inf."""
        value = log_loss(0.0, 1)
        assert math.isfinite(value)
        assert value > 10


class TestPairedBrier:
    def test_better_model_yields_positive_difference(self):
        rows = [
            _row(market=0.5, model=0.9, outcome=1),
            _row(market=0.5, model=0.9, outcome=1),
            _row(market=0.5, model=0.1, outcome=0),
            _row(market=0.5, model=0.1, outcome=0),
        ]
        result = paired_brier(rows)
        assert result["model_brier"] < result["market_brier"]
        assert result["mean_diff"] > 0
        assert result["t_stat"] > 0

    def test_worse_model_yields_negative_difference(self):
        rows = [
            _row(market=0.9, model=0.1, outcome=1),
            _row(market=0.9, model=0.1, outcome=1),
            _row(market=0.8, model=0.2, outcome=1),
        ]
        result = paired_brier(rows)
        assert result["mean_diff"] < 0
        assert result["t_stat"] < 0

    def test_identical_forecasts_cancel_exactly(self):
        rows = [_row(market=0.6, model=0.6, outcome=1) for _ in range(5)]
        result = paired_brier(rows)
        assert result["mean_diff"] == 0.0
        assert result["n"] == 5

    def test_scores_are_paired_on_the_same_events(self):
        """n must equal the row count, not some filtered subset."""
        rows = [_row(market=0.3, model=0.7, outcome=i % 2) for i in range(10)]
        assert paired_brier(rows)["n"] == 10


class TestCalibration:
    def test_well_calibrated_forecaster_matches_reality(self):
        """Seven of ten 0.7-forecasts resolve YES, so the bucket reads 0.7."""
        rows = [_row(0.5, 0.7, 1) for _ in range(7)]
        rows += [_row(0.5, 0.7, 0) for _ in range(3)]
        table = calibration(rows, bins=5)
        bucket = next(b for b in table if b["low"] <= 0.7 < b["high"])
        assert bucket["count"] == 10
        assert bucket["realised"] == 0.7

    def test_empty_buckets_are_omitted(self):
        rows = [_row(0.5, 0.05, 0) for _ in range(3)]
        table = calibration(rows, bins=5)
        assert len(table) == 1

    def test_probability_of_one_lands_in_the_top_bucket(self):
        rows = [_row(0.5, 1.0, 1)]
        table = calibration(rows, bins=5)
        assert len(table) == 1
        assert table[0]["count"] == 1


class TestFees:
    def test_fee_at_midpoint(self):
        """0.07 x 0.5 x 0.5 = $0.0175, rounded up to 2 cents."""
        assert _fee_cents(50) == 2

    def test_fee_shrinks_toward_the_extremes(self):
        assert _fee_cents(5) < _fee_cents(50)

    def test_fee_is_never_negative(self):
        assert _fee_cents(99) >= 0


class TestSimulate:
    def test_winning_yes_trade_nets_payout_minus_entry_and_fee(self):
        rows = [_row(market=0.40, model=0.80, outcome=1, yes_ask=40)]
        result = simulate(rows, edge=0.10, min_confidence=0.0)
        assert result["trades"] == 1
        assert result["wins"] == 1
        assert result["gross_cents"] == 60
        assert result["net_cents"] == 60 - _fee_cents(40)

    def test_losing_yes_trade_forfeits_the_entry(self):
        rows = [_row(market=0.40, model=0.80, outcome=0, yes_ask=40)]
        result = simulate(rows, edge=0.10, min_confidence=0.0)
        assert result["gross_cents"] == -40
        assert result["wins"] == 0

    def test_model_below_market_buys_no_side(self):
        rows = [_row(market=0.80, model=0.30, outcome=0, no_ask=20)]
        result = simulate(rows, edge=0.10, min_confidence=0.0)
        assert result["trades"] == 1
        assert result["wins"] == 1
        assert result["gross_cents"] == 80

    def test_small_edges_are_filtered_out(self):
        rows = [_row(market=0.50, model=0.52, outcome=1)]
        assert simulate(rows, edge=0.10, min_confidence=0.0)["trades"] == 0

    def test_low_confidence_is_filtered_out(self):
        rows = [_row(market=0.40, model=0.90, outcome=1, conf=0.2)]
        assert simulate(rows, edge=0.10, min_confidence=0.85)["trades"] == 0

    def test_no_trades_reports_zero_not_division_error(self):
        result = simulate([], edge=0.10, min_confidence=0.0)
        assert result["trades"] == 0
        assert result["win_rate"] == 0.0
        assert result["roi"] == 0.0

    def test_roi_is_relative_to_capital_actually_deployed(self):
        rows = [
            _row(market=0.40, model=0.80, outcome=1, yes_ask=40),
            _row(market=0.40, model=0.80, outcome=0, yes_ask=40),
        ]
        result = simulate(rows, edge=0.10, min_confidence=0.0)
        assert result["deployed_cents"] == 80
        assert result["gross_cents"] == 20
