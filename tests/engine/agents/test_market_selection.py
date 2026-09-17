"""Senses must only queue markets whose price means something.

Observed live: every opportunity Senses queued was a KXMVECROSSCATEGORY
combo shard with Volume: 0, and the Brain then scored them. Two causes:

  * No filtering, so the listing returned nothing but shards.
  * queue_from_stock read market["yes_price"], a key Kalshi no longer sends.
    It defaulted to 50, so every market was presented to the Brain as a
    coin flip regardless of its real price. The Brain was comparing its
    estimate against a number nobody quoted.
"""
import pytest

from agents.senses.scanner import (
    MAX_SPREAD_CENTS,
    MIN_VOLUME,
    is_tradeable,
    market_probability,
)


def _market(**overrides) -> dict:
    market = {
        "ticker": "KXNFLGAME-26SEP21NYGLAR-NYG",
        "yes_bid_dollars": "0.2500",
        "yes_ask_dollars": "0.2700",
        "last_price_dollars": "0.2600",
        "volume_fp": "5000.00",
    }
    market.update(overrides)
    return market


class TestMarketProbability:
    def test_uses_the_bid_ask_midpoint(self):
        assert market_probability(_market()) == pytest.approx(0.26)

    def test_falls_back_to_last_trade_when_unquoted(self):
        m = _market(yes_bid_dollars="0.0000", yes_ask_dollars="0.0000")
        assert market_probability(m) == pytest.approx(0.26)

    def test_returns_none_when_there_is_no_price_at_all(self):
        """The old code returned 0.50 here, inventing a price."""
        m = _market(
            yes_bid_dollars="0.0000",
            yes_ask_dollars="0.0000",
            last_price_dollars="0.0000",
        )
        assert market_probability(m) is None

    def test_ignores_the_legacy_yes_price_key(self):
        """Kalshi stopped sending yes_price; reading it produced 0.50."""
        m = _market(
            yes_price=99,
            yes_bid_dollars="0.1000",
            yes_ask_dollars="0.1200",
        )
        assert market_probability(m) == pytest.approx(0.11)

    def test_survives_a_non_numeric_value(self):
        assert market_probability(_market(yes_bid_dollars=None)) is not None


class TestIsTradeable:
    def test_accepts_a_liquid_tightly_quoted_market(self):
        assert is_tradeable(_market()) is True

    def test_rejects_combo_shards_by_prefix(self):
        """These dominated the listing and carry no information."""
        m = _market(ticker="KXMVECROSSCATEGORY-S2026AFF-E866")
        assert is_tradeable(m) is False

    def test_rejects_zero_volume(self):
        assert is_tradeable(_market(volume_fp="0.00")) is False

    def test_rejects_volume_below_the_floor(self):
        assert is_tradeable(_market(volume_fp=str(MIN_VOLUME - 1))) is False

    def test_accepts_volume_exactly_at_the_floor(self):
        assert is_tradeable(_market(volume_fp=str(MIN_VOLUME))) is True

    def test_rejects_an_unquoted_market(self):
        m = _market(yes_bid_dollars="0.0000", yes_ask_dollars="0.0000")
        assert is_tradeable(m) is False

    def test_rejects_a_spread_too_wide_to_price(self):
        wide = (MAX_SPREAD_CENTS + 2) / 100
        m = _market(yes_bid_dollars="0.2500", yes_ask_dollars=f"{0.25 + wide:.4f}")
        assert is_tradeable(m) is False

    def test_accepts_a_spread_exactly_at_the_limit(self):
        m = _market(
            yes_bid_dollars="0.2500",
            yes_ask_dollars=f"{0.25 + MAX_SPREAD_CENTS / 100:.4f}",
        )
        assert is_tradeable(m) is True

    def test_a_shard_is_rejected_even_if_it_somehow_has_volume(self):
        m = _market(ticker="KXMVECROSSCATEGORY-X", volume_fp="999999.00")
        assert is_tradeable(m) is False
