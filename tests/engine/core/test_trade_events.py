"""Executed trades must reach the dashboard.

The Hand published TRADE_RESULT on entry and POSITION_CLOSED on exit. Neither
was bridged to SSE, so the one thing the engine exists to do was the one thing
the dashboard could not show. The workflow graph even counted them --
`events.filter(e => e.type === 'TRADE')` -- against a union with no 'TRADE'
member, so that counter read zero however many orders were placed.
"""
import pytest

from core.event_formatter import format_trade_event


def test_an_entry_is_reported_as_an_open():
    event = format_trade_event(
        {"ticker": "KXBTC-25", "side": "no", "entry_price": 42, "stake": 2500},
        cycle_count=9,
    )

    assert event["type"] == "TRADE"
    assert event["trade"]["action"] == "OPEN"
    assert event["trade"]["ticker"] == "KXBTC-25"
    assert event["trade"]["side"] == "NO"
    assert event["trade"]["priceCents"] == 42
    assert event["trade"]["stakeCents"] == 2500
    assert event["trade"]["cycleId"] == 9


def test_an_exit_is_reported_as_a_close_with_its_reason():
    event = format_trade_event(
        {"ticker": "KXBTC-25", "price": 88, "reason": "take-profit"},
        cycle_count=9,
        closed=True,
    )

    assert event["trade"]["action"] == "CLOSE"
    assert event["trade"]["priceCents"] == 88
    assert event["trade"]["reason"] == "take-profit"


def test_entries_and_exits_share_a_shape():
    """A client should be able to render one timeline, not two unrelated feeds."""
    opened = format_trade_event({"ticker": "A", "entry_price": 10}, 1)
    closed = format_trade_event({"ticker": "A", "price": 90}, 1, closed=True)

    assert opened["trade"].keys() == closed["trade"].keys()


def test_every_trade_gets_its_own_id():
    a = format_trade_event({"ticker": "A"}, 1)
    b = format_trade_event({"ticker": "A"}, 1)

    assert a["trade"]["id"] != b["trade"]["id"]


def test_a_sparse_payload_does_not_raise():
    """A formatter that throws would take down the broadcast for every client."""
    event = format_trade_event({}, 0)

    assert event["trade"]["ticker"] == "UNKNOWN"
    assert event["trade"]["side"] == "YES"


def test_the_bridge_subscribes_to_both_trade_topics():
    """Registering the formatter without subscribing would change nothing."""
    import inspect

    from http_api import routes

    source = inspect.getsource(routes)
    assert 'subscribe("TRADE_RESULT"' in source
    assert 'subscribe("POSITION_CLOSED"' in source
