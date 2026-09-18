"""The Orders panel reads executed orders straight from the decision ledger.

recent_fills has to reconstruct the ticket (side, price, count) from what
record_fill stored, and report realised P&L only once the market settled.
"""

import pytest
from core import ledger


@pytest.fixture(autouse=True)
def isolated_ledger(tmp_path, monkeypatch):
    monkeypatch.setenv("GHOST_LEDGER_DB", str(tmp_path / "ledger.db"))
    yield


def _approve_and_fill(ticker, price, order_id, stake=200):
    ledger.record_decision(
        ticker, price, outcome="APPROVED", estimated_probability=price + 0.05, confidence=0.9
    )
    ledger.record_fill(ticker, stake, order_id)


class TestRecentFills:
    def test_only_filled_decisions_are_returned_newest_first(self):
        ledger.record_decision("VETO", 0.5, outcome="VETOED", veto_reason="edge")
        _approve_and_fill("A", 0.23, "PAPER-buy-no-A-77x2")
        _approve_and_fill("B", 0.60, "PAPER-buy-yes-B-60x3")

        fills = ledger.recent_fills()

        assert [f["ticker"] for f in fills] == ["B", "A"]
        assert all(f["order_id"] for f in fills)

    def test_paper_order_id_yields_side_price_and_count(self):
        _approve_and_fill(
            "KXNFLGAME-26SEP21NYGLAR-LAR", 0.77, "PAPER-buy-no-KXNFLGAME-26SEP21NYGLAR-LAR-23x8"
        )

        (fill,) = ledger.recent_fills()

        assert (fill["side"], fill["price_cents"], fill["count"]) == ("no", 23, 8)
        assert fill["pnl_cents"] is None  # not settled yet

    def test_settlement_produces_realised_pnl_for_the_held_side(self):
        _approve_and_fill("Y", 0.40, "PAPER-buy-yes-Y-40x5")
        _approve_and_fill("N", 0.70, "PAPER-buy-no-N-30x4")
        ledger.record_settlement("Y", settled_yes=True)  # YES holder wins 60c x 5
        ledger.record_settlement("N", settled_yes=True)  # NO holder loses 30c x 4

        by_ticker = {f["ticker"]: f for f in ledger.recent_fills()}

        assert by_ticker["Y"]["pnl_cents"] == 300
        assert by_ticker["N"]["pnl_cents"] == -120

    def test_a_real_order_id_falls_back_to_the_market_price(self):
        _approve_and_fill("R", 0.50, "kalshi-uuid-1234", stake=150)

        (fill,) = ledger.recent_fills()

        assert (fill["side"], fill["price_cents"], fill["count"]) == ("yes", 50, 3)

    def test_limit_is_honoured(self):
        for i in range(5):
            _approve_and_fill(f"T{i}", 0.5, f"PAPER-buy-yes-T{i}-50x1")

        assert len(ledger.recent_fills(limit=2)) == 2
