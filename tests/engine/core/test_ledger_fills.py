"""Executed orders must reach the ledger, or paper P&L cannot be measured.

stake_cents and order_id were columns from the first schema and nothing ever
wrote them. Five paper fills in one run left zero filled rows. A paper soak
that cannot report what it staked is not measuring anything.
"""

import pytest
from core import ledger


@pytest.fixture(autouse=True)
def isolated_ledger(tmp_path, monkeypatch):
    monkeypatch.setenv("GHOST_LEDGER_DB", str(tmp_path / "ledger.db"))
    yield


def _filled_rows():
    with ledger._connect() as conn:
        return conn.execute(
            "SELECT ticker, outcome, stake_cents, order_id FROM decisions "
            "WHERE order_id IS NOT NULL ORDER BY id"
        ).fetchall()


class TestFillsAttachToTheirDecision:
    def test_the_regression_a_fill_is_recorded(self):
        ledger.record_decision(
            "T", 0.35, outcome="APPROVED", estimated_probability=0.37, confidence=0.85
        )

        updated = ledger.record_fill("T", 245, "PAPER-buy-yes-T-35x7")

        assert updated == 1
        assert _filled_rows() == [("T", "APPROVED", 245, "PAPER-buy-yes-T-35x7")]

    def test_a_fill_with_no_approved_decision_updates_nothing(self):
        ledger.record_decision("T", 0.35, outcome="VETOED", veto_reason="edge")

        assert ledger.record_fill("T", 245, "X") == 0
        assert _filled_rows() == []

    def test_two_fills_on_one_market_attach_to_two_decisions(self):
        """The second must not overwrite the first."""
        ledger.record_decision("T", 0.35, outcome="APPROVED")
        ledger.record_decision("T", 0.35, outcome="APPROVED")

        assert ledger.record_fill("T", 100, "first") == 1
        assert ledger.record_fill("T", 200, "second") == 1

        rows = _filled_rows()
        assert len(rows) == 2
        assert {r[3] for r in rows} == {"first", "second"}

    def test_the_latest_unfilled_approval_is_chosen(self):
        ledger.record_decision("T", 0.30, outcome="APPROVED")
        ledger.record_decision("T", 0.35, outcome="APPROVED")

        ledger.record_fill("T", 100, "only")

        with ledger._connect() as conn:
            price = conn.execute(
                "SELECT market_price FROM decisions WHERE order_id = 'only'"
            ).fetchone()[0]
        assert price == 0.35

    def test_other_tickers_are_untouched(self):
        ledger.record_decision("A", 0.5, outcome="APPROVED")
        ledger.record_decision("B", 0.5, outcome="APPROVED")

        ledger.record_fill("A", 100, "a-fill")

        rows = _filled_rows()
        assert [r[0] for r in rows] == ["A"]

    def test_a_third_fill_with_nothing_left_to_attach_to_is_a_no_op(self):
        ledger.record_decision("T", 0.35, outcome="APPROVED")
        ledger.record_fill("T", 100, "first")

        assert ledger.record_fill("T", 100, "orphan") == 0
