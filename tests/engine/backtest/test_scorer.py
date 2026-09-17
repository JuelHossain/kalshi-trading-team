"""Scoring the engine against settled markets.

The ledger answers calibration going forward, one settlement at a time. It
cannot answer it retrospectively, so before this the only way to learn whether
the strategy had edge was to risk money and wait. Kalshi markets settle, which
makes every past market labelled data.
"""

import random

import pytest
from backtest.runner import format_report
from backtest.scorer import score_predictions


def _row(probability, price, settled_yes, confidence=0.95):
    return {
        "probability": probability,
        "price": price,
        "settled_yes": settled_yes,
        "confidence": confidence,
    }


class TestTradeSelection:
    def test_a_thin_edge_is_not_traded(self):
        result = score_predictions([_row(0.52, 0.50, True)], min_edge=0.05)
        assert result.n == 1 and result.traded == 0

    def test_a_sufficient_edge_is_traded(self):
        result = score_predictions([_row(0.60, 0.50, True)], min_edge=0.05)
        assert result.traded == 1

    def test_low_confidence_is_skipped(self):
        result = score_predictions([_row(0.90, 0.50, True, confidence=0.10)])
        assert result.traded == 0

    def test_a_missing_confidence_does_not_block_the_trade(self):
        row = _row(0.90, 0.50, True)
        del row["confidence"]
        assert score_predictions([row]).traded == 1

    def test_an_overpriced_market_is_scored_as_a_no_trade(self):
        """Scoring YES-only would damn a strategy the engine does not run."""
        # Estimate 0.20 against a 0.70 price: NO at 30c, and the event did not
        # happen, so the trade won.
        result = score_predictions([_row(0.20, 0.70, False)])
        assert result.traded == 1
        assert result.wins == 1

    def test_a_losing_no_trade_is_counted_as_a_loss(self):
        result = score_predictions([_row(0.20, 0.70, True)])
        assert result.traded == 1
        assert result.wins == 0
        assert result.total_return == pytest.approx(-1.0)


class TestReturns:
    def test_a_winning_trade_pays_the_implied_odds(self):
        """Buying at 40c and winning returns 60/40 = 1.5 per $1 staked."""
        result = score_predictions([_row(0.80, 0.40, True)])
        assert result.total_return == pytest.approx(1.5)

    def test_a_losing_trade_costs_the_stake(self):
        result = score_predictions([_row(0.80, 0.40, False)])
        assert result.total_return == pytest.approx(-1.0)

    def test_nothing_traded_reports_no_rate(self):
        result = score_predictions([_row(0.51, 0.50, True)])
        assert result.hit_rate is None
        assert "nothing to judge" in result.summary()


class TestBadRowsAreIgnoredNotGuessed:
    @pytest.mark.parametrize(
        "row",
        [
            {"probability": None, "price": 0.5, "settled_yes": True},
            {"probability": 0.6, "price": None, "settled_yes": True},
            {"probability": 0.6, "price": 0.5, "settled_yes": None},
            {"probability": 1.5, "price": 0.5, "settled_yes": True},
            {"probability": 0.6, "price": 0.0, "settled_yes": True},
            {"probability": 0.6, "price": 1.0, "settled_yes": True},
        ],
    )
    def test_unusable_rows_are_not_scored(self, row):
        assert score_predictions([row]).n == 0


class TestCalibrationSeparatesSkillFromNoise:
    def test_a_skilled_forecaster_scores_well(self):
        random.seed(11)
        rows = []
        for _ in range(400):
            truth = random.random()
            estimate = min(0.99, max(0.01, truth + random.gauss(0, 0.08)))
            price = min(0.99, max(0.01, truth + random.gauss(0, 0.12)))
            rows.append(_row(estimate, price, random.random() < truth))

        result = score_predictions(rows)

        assert result.brier < 0.20
        assert all(abs(b["gap"]) < 0.15 for b in result.calibration)

    def test_noise_is_exposed_however_profitable_it_looks(self):
        """The trap: pure noise can post a profit when cheap long shots land."""
        random.seed(11)
        rows = []
        for _ in range(400):
            truth = random.random()
            price = min(0.99, max(0.01, truth + random.gauss(0, 0.12)))
            rows.append(_row(random.random(), price, random.random() < truth))

        result = score_predictions(rows)
        report = format_report(result)

        assert result.brier > 0.25, "noise was not distinguished from skill"
        assert max(abs(b["gap"]) for b in result.calibration) > 0.30
        if (result.return_per_trade or 0) > 0:
            assert "WARNING" in report, "a profitable coin flip was not flagged"

    def test_brier_covers_every_estimate_not_only_traded_ones(self):
        """Calibration is a property of the forecaster, not of the filter."""
        rows = [_row(0.51, 0.50, True), _row(0.52, 0.50, False)]  # neither traded
        result = score_predictions(rows)
        assert result.traded == 0
        assert result.brier is not None
