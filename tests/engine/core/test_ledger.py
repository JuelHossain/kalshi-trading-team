"""The decision ledger is how we find out whether the engine is any good.

Without it there is no way to ask whether an 80% call resolves true 80% of the
time -- and a model that is confidently, consistently wrong looks identical
from the outside to one that is right, until the money is gone.
"""

import pytest

from core.ledger import calibration, realised_edge, record_decision, record_settlement


class TestRecording:
    def test_a_decision_is_recorded(self):
        assert record_decision("KXA", 0.50, "APPROVED", estimated_probability=0.7) > 0

    def test_edge_is_derived_not_supplied(self):
        record_decision("KXB", 0.40, "APPROVED", estimated_probability=0.75)
        record_settlement("KXB", settled_yes=True)
        assert realised_edge()["expected"] == pytest.approx(0.35)

    def test_vetoes_are_recorded_too(self):
        """A veto is a prediction. A bot that vetoes its winners is worth catching."""
        record_decision("KXC", 0.50, "VETOED", estimated_probability=0.52,
                        veto_reason="edge below minimum")
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

        bucket = [b for b in calibration() if b["n"] == 100][0]
        assert bucket["predicted"] == pytest.approx(0.80)
        assert bucket["actual"] == pytest.approx(0.80)
        assert abs(bucket["gap"]) < 0.01

    def test_an_overconfident_forecaster_is_exposed(self):
        """The failure mode this exists to catch."""
        for i in range(100):
            record_decision(f"O{i}", 0.5, "APPROVED", estimated_probability=0.90)
            record_settlement(f"O{i}", settled_yes=i < 50)  # claims 90%, delivers 50%

        bucket = [b for b in calibration() if b["n"] == 100][0]
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
