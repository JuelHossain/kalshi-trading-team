"""The decision ledger is how we find out whether the engine is any good.

Without it there is no way to ask whether an 80% call resolves true 80% of the
time -- and a model that is confidently, consistently wrong looks identical
from the outside to one that is right, until the money is gone.
"""

import pytest
from core.ledger import calibration, realised_edge, record_decision, record_fill, record_settlement


class TestRecording:
    def test_a_decision_is_recorded(self):
        assert record_decision("KXA", 0.50, "APPROVED", estimated_probability=0.7) > 0

    def test_edge_is_derived_not_supplied(self):
        record_decision("KXB", 0.40, "APPROVED", estimated_probability=0.75)
        record_settlement("KXB", settled_yes=True)
        assert realised_edge()["expected"] == pytest.approx(0.35)

    def test_vetoes_are_recorded_too(self):
        """A veto is a prediction. A bot that vetoes its winners is worth catching."""
        record_decision(
            "KXC", 0.50, "VETOED", estimated_probability=0.52, veto_reason="edge below minimum"
        )
        record_settlement("KXC", settled_yes=True)
        assert calibration()[0]["n"] == 1

    def test_a_ledger_failure_never_reaches_the_caller(self, monkeypatch):
        """Recording must not be able to stop a trade."""
        import core.ledger

        def boom(*_a, **_k):
            raise RuntimeError("disk gone")

        monkeypatch.setattr(core.ledger, "_connect", boom)
        assert record_decision("KXD", 0.5, "APPROVED") == -1
        assert record_settlement("KXD", True) == 0


class TestCalibration:
    def test_no_settled_data_reports_nothing(self):
        record_decision("KXE", 0.5, "APPROVED", estimated_probability=0.9)
        assert calibration() == []

    def test_a_calibrated_forecaster_shows_a_small_gap(self):
        for i in range(100):
            record_decision(f"C{i}", 0.5, "APPROVED", estimated_probability=0.80)
            record_settlement(f"C{i}", settled_yes=i < 80)  # exactly 80%

        bucket = next(b for b in calibration() if b["n"] == 100)
        assert bucket["predicted"] == pytest.approx(0.80)
        assert bucket["actual"] == pytest.approx(0.80)
        assert abs(bucket["gap"]) < 0.01

    def test_an_overconfident_forecaster_is_exposed(self):
        """The failure mode this exists to catch."""
        for i in range(100):
            record_decision(f"O{i}", 0.5, "APPROVED", estimated_probability=0.90)
            record_settlement(f"O{i}", settled_yes=i < 50)  # claims 90%, delivers 50%

        bucket = next(b for b in calibration() if b["n"] == 100)
        assert bucket["gap"] < -0.3, "a 40-point miss was not surfaced"


class TestRealisedEdge:
    def test_expected_and_realised_are_compared(self):
        # Bought at 50c believing 90%. Settles yes half the time.
        for i in range(100):
            record_decision(f"R{i}", 0.50, "APPROVED", estimated_probability=0.90)
            record_settlement(f"R{i}", settled_yes=i < 50)

        result = realised_edge()
        assert result["n"] == 100
        assert result["expected"] == pytest.approx(0.40)
        assert result["realised"] == pytest.approx(0.00, abs=0.01)
        assert result["gap"] < -0.35

    def test_only_traded_decisions_count_toward_realised_edge(self):
        """A veto has no P&L, so it cannot appear in realised performance."""
        record_decision("V1", 0.5, "VETOED", estimated_probability=0.9)
        record_settlement("V1", settled_yes=True)
        assert realised_edge()["n"] == 0


class TestRealisedEdgeIsSideAware:
    """market_price and edge are always recorded in YES terms (Brain reads
    the YES market price regardless of which side it goes on to buy -- see
    agents/brain/agent.py). Buying NO at 70c because the model believes YES
    is worth 75% is the same bet as buying YES at 30c believing the same
    thing, and must score the same way. Treating every fill as a YES
    purchase silently flipped the sign of every live NO trade's reported
    P&L.
    """

    def test_a_winning_no_trade_has_positive_realised_pnl(self):
        record_decision("N1", 0.30, "APPROVED", estimated_probability=0.75)
        record_fill("N1", 700, "kalshi-uuid-1", side="no", price_cents=70, count=10)
        record_settlement("N1", settled_yes=False)  # NO happened: the NO holder wins

        result = realised_edge()

        assert result["n"] == 1
        assert result["realised"] == pytest.approx(0.30)  # 1 - 0.70
        assert result["expected"] == pytest.approx(-0.45)  # -(0.75 - 0.30)

    def test_a_losing_no_trade_has_negative_realised_pnl(self):
        record_decision("N2", 0.30, "APPROVED", estimated_probability=0.75)
        record_fill("N2", 700, "kalshi-uuid-2", side="no", price_cents=70, count=10)
        record_settlement("N2", settled_yes=True)  # YES happened: the NO holder loses

        result = realised_edge()

        assert result["realised"] == pytest.approx(-0.70)

    def test_yes_and_no_trades_combine_correctly(self):
        record_decision("Y1", 0.40, "APPROVED", estimated_probability=0.80)
        record_fill("Y1", 400, "kalshi-uuid-3", side="yes", price_cents=40, count=10)
        record_settlement("Y1", settled_yes=True)  # realised (1 - 0.40) = 0.60

        record_decision("N3", 0.30, "APPROVED", estimated_probability=0.75)
        record_fill("N3", 700, "kalshi-uuid-4", side="no", price_cents=70, count=10)
        record_settlement("N3", settled_yes=False)  # realised (1 - 0.70) = 0.30

        result = realised_edge()

        assert result["n"] == 2
        assert result["realised"] == pytest.approx((0.60 + 0.30) / 2)

    def test_a_legacy_paper_order_id_recovers_its_own_side(self):
        """Rows written before side/price_cents/count existed have no stored
        ticket. A PAPER- order id still encodes its own side and price, the
        same recovery recent_fills makes via _parse_order_id -- defaulting
        the side to "yes" here (as this used to) flipped the sign for a NO
        fill exactly like a real order id with no ticket would.
        """
        record_decision("P1", 0.30, "APPROVED", estimated_probability=0.75)
        record_fill("P1", 700, "PAPER-buy-no-P1-70x10")  # no side/price_cents/count
        record_settlement("P1", settled_yes=False)  # NO happened: the NO holder wins

        result = realised_edge()

        assert result["realised"] == pytest.approx(0.30)  # 1 - 0.70, not -0.70
        assert result["expected"] == pytest.approx(-0.45)
