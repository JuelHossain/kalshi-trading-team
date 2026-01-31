import pytest
from engine.core.synapse import MarketData, Opportunity, ExecutionSignal, SynapseError
from datetime import datetime

def test_market_data_schema():
    data = {
        "ticker": "TEST-123",
        "title": "Will it rain?",
        "subtitle": "NYC",
        "yes_price": 50,
        "no_price": 50,
        "volume": 1000,
        "expiration": "2026-01-30",
        "raw_response": {"foo": "bar"}
    }
    obj = MarketData(**data)
    assert obj.ticker == "TEST-123"
    assert obj.raw_response["foo"] == "bar"

def test_opportunity_schema():
    md = MarketData(ticker="T", title="T", subtitle="S", yes_price=50, no_price=50, volume=0, expiration="")
    opp = Opportunity(ticker="T", market_data=md, priority=5)
    assert opp.priority == 5
    assert isinstance(opp.timestamp, datetime)

def test_execution_signal_schema():
    md = MarketData(ticker="T", title="T", subtitle="S", yes_price=50, no_price=50, volume=0, expiration="")
    opp = Opportunity(ticker="T", market_data=md)
    sig = ExecutionSignal(
        target_opportunity=opp,
        action="BUY",
        side="YES",
        confidence=0.8,
        monte_carlo_ev=1.5,
        reasoning="Good odds",
        suggested_count=10
    )
    assert sig.status == "PENDING"
    assert sig.target_opportunity.ticker == "T"
