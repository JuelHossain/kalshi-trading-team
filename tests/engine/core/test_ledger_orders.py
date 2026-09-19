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

    def test_a_stored_ticket_is_used_instead_of_guessing(self):
        """hand/agent.py now always passes record_fill the actual ticket.

        Before, a real Kalshi order id carried no side or price, so
        _parse_order_id always guessed "yes" at the YES market price -- right
        for a YES fill, backwards for a NO one. This is the ticket a live NO
        buy now stores.
        """
        ledger.record_decision("R2", 0.30, outcome="APPROVED", estimated_probability=0.75)
        ledger.record_fill("R2", 700, "kalshi-uuid-5678", side="no", price_cents=70, count=10)

        (fill,) = ledger.recent_fills()

        assert (fill["side"], fill["price_cents"], fill["count"]) == ("no", 70, 10)

    def test_a_live_no_fill_settles_with_the_correct_pnl_sign(self):
        """The regression: a live NO trade's P&L must not be reported as
        though it were a YES trade bought at the YES market price."""
        ledger.record_decision("R3", 0.30, outcome="APPROVED", estimated_probability=0.75)
        ledger.record_fill("R3", 700, "kalshi-uuid-9999", side="no", price_cents=70, count=10)
        ledger.record_settlement("R3", settled_yes=False)  # NO happened: the NO holder wins

        (fill,) = ledger.recent_fills()

        assert fill["pnl_cents"] == 300  # (100 - 70)c x 10 contracts

    def test_limit_is_honoured(self):
        for i in range(5):
            _approve_and_fill(f"T{i}", 0.5, f"PAPER-buy-yes-T{i}-50x1")

        assert len(ledger.recent_fills(limit=2)) == 2


class TestExitPricing:
    """A position closed early (check_exits, Ragnarok) must be priced off its
    own exit, not off however the market eventually settles. Without
    record_exit, a take-profit exit that the market went on to settle
    against reported the settlement loss, and a stop-loss that the market
    settled for reported a win that never happened.
    """

    def test_a_yes_take_profit_reports_the_profit_even_though_the_market_settles_no(self):
        # 10 YES bought at 40c, exited at 90c (+$5.00 realised), then the
        # market settles NO -- which would look like a $4.00 loss if this
        # fill were still priced off settlement.
        ledger.record_decision("YTP", 0.40, outcome="APPROVED", estimated_probability=0.85)
        ledger.record_fill("YTP", 400, "kalshi-order-ytp", side="yes", price_cents=40, count=10)

        ledger.record_exit("YTP", "yes", 90)
        ledger.record_settlement("YTP", settled_yes=False)

        (fill,) = ledger.recent_fills()
        assert fill["pnl_cents"] == 500
        assert fill["exit_price_cents"] == 90
        assert fill["closed"] is True
        assert fill["settled_yes"] == 0  # calibration still gets the outcome

    def test_a_no_take_profit_reports_the_profit_even_though_the_market_settles_yes(self):
        # 10 NO bought at 40c, exited at the NO bid of 90c, then the market
        # settles YES -- the NO holder's settlement result would be a loss.
        ledger.record_decision("NTP", 0.60, outcome="APPROVED", estimated_probability=0.15)
        ledger.record_fill("NTP", 400, "kalshi-order-ntp", side="no", price_cents=40, count=10)

        ledger.record_exit("NTP", "no", 90)
        ledger.record_settlement("NTP", settled_yes=True)

        (fill,) = ledger.recent_fills()
        assert fill["pnl_cents"] == 500

    def test_a_yes_stop_loss_reports_the_loss_even_though_the_market_settles_yes(self):
        # 10 YES bought at 60c, stopped out at 20c (-$4.00 realised), then
        # the market settles YES -- which would look like a $4.00 win (a
        # loss reported as a win) if this fill were still priced off
        # settlement.
        ledger.record_decision("YSL", 0.60, outcome="APPROVED", estimated_probability=0.30)
        ledger.record_fill("YSL", 600, "kalshi-order-ysl", side="yes", price_cents=60, count=10)

        ledger.record_exit("YSL", "yes", 20)
        ledger.record_settlement("YSL", settled_yes=True)

        (fill,) = ledger.recent_fills()
        assert fill["pnl_cents"] == -400

    def test_an_exit_shows_closed_before_the_market_ever_settles(self):
        """The gap between an exit and settlement can be days; the Orders
        panel must not keep reporting the position as open in the meantime."""
        _approve_and_fill("OPEN-THEN-EXIT", 0.5, "kalshi-order-open-then-exit")
        ledger.record_exit("OPEN-THEN-EXIT", "yes", 70)

        (fill,) = ledger.recent_fills()
        assert fill["closed"] is True
        assert fill["settled_yes"] is None  # not settled yet -- still exited

    def test_an_unsettled_unexited_fill_is_open(self):
        _approve_and_fill("STILL-OPEN", 0.5, "kalshi-order-still-open")

        (fill,) = ledger.recent_fills()
        assert fill["closed"] is False

    def test_record_exit_does_not_touch_an_already_settled_row(self):
        """A row that already settled must not be reclassified as an exit
        after the fact -- settlement already recorded the true outcome."""
        _approve_and_fill("ALREADY-SETTLED", 0.5, "kalshi-order-already-settled")
        ledger.record_settlement("ALREADY-SETTLED", settled_yes=True)

        rows = ledger.record_exit("ALREADY-SETTLED", "yes", 10)

        assert rows == 0
        (fill,) = ledger.recent_fills()
        assert fill["exit_price_cents"] is None

    def test_an_unpriced_exit_is_not_restamped_by_a_later_unrelated_exit(self):
        """The book could not be read at the first exit, so that row is
        marked exited with no price. A second, unrelated position on the
        same ticker and side is entered and exited later -- that exit must
        match only the still-open second fill, not re-stamp the first row
        (which already has its own, separate exit)."""
        ledger.record_decision("REENTRY", 0.60, outcome="APPROVED", estimated_probability=0.30)
        ledger.record_fill(
            "REENTRY", 600, "kalshi-order-reentry-1", side="yes", price_cents=60, count=10
        )
        ledger.record_exit("REENTRY", "yes", None)  # book unreadable at the first exit

        ledger.record_decision("REENTRY", 0.30, outcome="APPROVED", estimated_probability=0.75)
        ledger.record_fill(
            "REENTRY", 300, "kalshi-order-reentry-2", side="yes", price_cents=30, count=10
        )
        rows = ledger.record_exit("REENTRY", "yes", 80)

        assert rows == 1  # only the second position's fill, not the first

        fills = {f["order_id"]: f for f in ledger.recent_fills()}
        assert fills["kalshi-order-reentry-1"]["exit_price_cents"] is None
        assert fills["kalshi-order-reentry-2"]["exit_price_cents"] == 80

    def test_a_legacy_no_fill_with_no_stored_side_is_matched_by_its_own_side(self):
        """Rows written before side/price_cents/count existed (b111d16) have
        side NULL. Resolved via _parse_order_id, the same recovery
        recent_fills/realised_edge use -- not defaulted to "yes"."""
        ledger.record_decision("LEGACY-NO", 0.30, outcome="APPROVED", estimated_probability=0.75)
        ledger.record_fill("LEGACY-NO", 700, "PAPER-buy-no-LEGACY-NO-70x10")  # no ticket stored

        rows = ledger.record_exit("LEGACY-NO", "no", 20)

        assert rows == 1
        (fill,) = ledger.recent_fills()
        assert fill["exit_price_cents"] == 20

    def test_a_legacy_no_fill_is_not_wrongly_matched_by_a_yes_exit(self):
        """Defaulting a NULL side to "yes" (COALESCE(side, 'yes')) let a YES
        exit on the same ticker wrongly mark a legacy NO fill -- the same
        default-to-yes mistake realised_edge's docstring already covers."""
        ledger.record_decision("LEGACY-NO2", 0.30, outcome="APPROVED", estimated_probability=0.75)
        ledger.record_fill("LEGACY-NO2", 700, "PAPER-buy-no-LEGACY-NO2-70x10")

        rows = ledger.record_exit("LEGACY-NO2", "yes", 20)

        assert rows == 0
        (fill,) = ledger.recent_fills()
        assert fill["exit_price_cents"] is None
