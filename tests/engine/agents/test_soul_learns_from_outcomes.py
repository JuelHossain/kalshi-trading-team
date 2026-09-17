"""The Soul must only learn from trades that have resolved.

Observed live: "Loss recorded. Lesson: ..." immediately after every one of
five paper fills. The Hand publishes TRADE_RESULT with outcome "pending" at
fill time; on_trade_result had `if outcome == "win": ... else: loss`, so a
trade was filed as a mistake before the game had been played, and
evolve_instructions then rewrote the trading rules from that log.
"""
import pytest

from agents.soul.agent import SoulAgent


class _Msg:
    def __init__(self, **payload):
        self.payload = payload


@pytest.fixture
def soul():
    agent = SoulAgent.__new__(SoulAgent)
    agent.strengths_list = []
    agent.mistakes_log = []
    agent.logged = []

    async def log(message, level="INFO"):
        agent.logged.append((message, level))

    agent.log = log
    return agent


class TestPendingIsNotALoss:
    @pytest.mark.asyncio
    async def test_a_fill_is_not_a_mistake(self, soul):
        """The regression: every fill went straight into mistakes_log."""
        await soul.on_trade_result(_Msg(outcome="pending", details="T at 35c"))

        assert soul.mistakes_log == []
        assert soul.strengths_list == []

    @pytest.mark.asyncio
    async def test_a_fill_is_noted_quietly(self, soul):
        await soul.on_trade_result(_Msg(outcome="pending", details="T at 35c"))

        assert soul.logged
        message, level = soul.logged[-1]
        assert level == "DEBUG"
        assert "Loss" not in message

    @pytest.mark.asyncio
    async def test_an_unknown_outcome_teaches_nothing(self, soul):
        await soul.on_trade_result(_Msg(details="no outcome key at all"))

        assert soul.mistakes_log == []
        assert soul.strengths_list == []


class TestSettledOutcomesStillTeach:
    @pytest.mark.asyncio
    async def test_a_win_is_a_strength(self, soul):
        await soul.on_trade_result(_Msg(outcome="win", details="T won"))

        assert soul.strengths_list == ["T won"]
        assert soul.mistakes_log == []

    @pytest.mark.asyncio
    async def test_a_loss_is_a_lesson(self, soul):
        await soul.on_trade_result(_Msg(outcome="loss", details="T lost"))

        assert soul.mistakes_log == ["T lost"]
        assert soul.strengths_list == []
