"""Queue wait must not discard half of every batch.

Observed live: "[STALE] Opportunity expired: ... (Age: 65s)" and "(Age:
74s)" on the back half of a ten-market batch. The threshold was a hardcoded
60 seconds, tuned when an estimate took about two. Search-grounded estimates
take about fifteen, so items five through ten of every batch were rejected
unanalysed -- and the Brain's own log showed it, every cycle.

The check measures time spent waiting in the queue, not market movement.
Execution freshness is the Hand's job: it re-reads the live orderbook
before any order.
"""
import importlib
from datetime import datetime, timedelta

import pytest

from agents.brain import monitor
from core import constants


async def _log(message, level="INFO"):
    pass


def _aged(seconds: float) -> dict:
    return {
        "ticker": "T",
        "timestamp": (datetime.now() - timedelta(seconds=seconds)).isoformat(),
    }


class TestBatchesSurviveGroundedLatency:
    def test_the_regression_seventy_four_seconds_is_fresh(self):
        """Age observed on the last item of a real batch."""
        is_fresh, status = monitor.check_opportunity_freshness(_aged(74), _log)
        assert (is_fresh, status) == (True, "FRESH")

    def test_a_full_grounded_batch_is_fresh(self):
        """Ten items at ~15s each: the last one waits ~150s."""
        is_fresh, _ = monitor.check_opportunity_freshness(_aged(150), _log)
        assert is_fresh is True

    def test_the_default_is_at_least_ten_grounded_calls(self):
        assert constants.BRAIN_STALE_OPPORTUNITY_SECONDS >= 150


class TestGenuinelyOldSnapshotsAreStillRefused:
    def test_beyond_the_threshold_is_stale(self):
        too_old = constants.BRAIN_STALE_OPPORTUNITY_SECONDS + 1
        is_fresh, status = monitor.check_opportunity_freshness(_aged(too_old), _log)
        assert (is_fresh, status) == (False, "STALE")

    def test_exactly_at_the_threshold_is_stale(self):
        """Boundary kept as >= ; a snapshot that old is from another cycle."""
        at = constants.BRAIN_STALE_OPPORTUNITY_SECONDS
        is_fresh, _ = monitor.check_opportunity_freshness(_aged(at), _log)
        assert is_fresh is False

    def test_no_timestamp_is_refused_for_safety(self):
        is_fresh, status = monitor.check_opportunity_freshness({"ticker": "T"}, _log)
        assert (is_fresh, status) == (False, "STALE")

    def test_an_unparseable_timestamp_is_refused(self):
        bad = {"ticker": "T", "timestamp": "yesterday-ish"}
        is_fresh, _ = monitor.check_opportunity_freshness(bad, _log)
        assert is_fresh is False


class TestThresholdIsOperatorTunable:
    def test_env_override_is_honoured(self, monkeypatch):
        monkeypatch.setenv("BRAIN_STALE_OPPORTUNITY_SECONDS", "20")
        try:
            reloaded = importlib.reload(constants)
            assert reloaded.BRAIN_STALE_OPPORTUNITY_SECONDS == 20.0
        finally:
            monkeypatch.delenv("BRAIN_STALE_OPPORTUNITY_SECONDS", raising=False)
            importlib.reload(constants)
            importlib.reload(monitor)
