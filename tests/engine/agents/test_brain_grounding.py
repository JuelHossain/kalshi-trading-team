"""The Brain must estimate from current information, not memory.

Ungrounded, the model answers a dated question from training data. Measured
on one NFL market, same model and prompt:

    ungrounded  p=0.38 confidence=45  "Assuming the matchup takes place..."
    grounded    p=0.25 confidence=85  quoting current betting lines

The real Kalshi price was 0.26. Ungrounded estimates landed below the 85%
confidence threshold, so the engine vetoed everything and never traded --
safe, but useless. Worse, ungrounded confidence is not honest: elsewhere the
same model priced a central-bank market at 0.01 with 95% confidence by citing
a rate decision from the wrong year.
"""

import importlib

import pytest
from agents.brain import debate


@pytest.fixture
def reload_debate(monkeypatch):
    """Re-import the module so the env var is read at import time."""

    def _reload(value: str | None):
        if value is None:
            monkeypatch.delenv("BRAIN_SEARCH_GROUNDING", raising=False)
        else:
            monkeypatch.setenv("BRAIN_SEARCH_GROUNDING", value)
        return importlib.reload(debate)

    yield _reload
    monkeypatch.delenv("BRAIN_SEARCH_GROUNDING", raising=False)
    importlib.reload(debate)


class TestGroundingDefault:
    def test_grounding_is_on_unless_switched_off(self, reload_debate):
        assert reload_debate(None).GROUNDING_ENABLED is True

    def test_config_requests_google_search(self, reload_debate):
        config = reload_debate(None).build_grounding_config()

        assert config is not None
        assert config.tools, "grounding config carries no tools"
        assert config.tools[0].google_search is not None


class TestGroundingDisabled:
    @pytest.mark.parametrize("value", ["false", "False", "0", "no", "NO"])
    def test_recognised_off_values(self, reload_debate, value):
        module = reload_debate(value)

        assert module.GROUNDING_ENABLED is False
        assert module.build_grounding_config() is None

    @pytest.mark.parametrize("value", ["true", "yes", "1", "anything"])
    def test_anything_else_leaves_it_on(self, reload_debate, value):
        assert reload_debate(value).GROUNDING_ENABLED is True

    def test_whitespace_is_tolerated(self, reload_debate):
        assert reload_debate("  false  ").GROUNDING_ENABLED is False


class TestGroundingIsNotLoadBearing:
    def test_missing_sdk_degrades_instead_of_crashing(self, reload_debate, monkeypatch):
        """An SDK change must not take the Brain offline.

        A degraded estimate still beats no estimate: the confidence
        threshold is what stops a bad one reaching the Hand.
        """
        module = reload_debate(None)
        real_import = importlib.__import__

        def _no_genai(name, *args, **kwargs):
            if name == "google.genai":
                raise ImportError("simulated SDK change")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", _no_genai)

        assert module.build_grounding_config() is None


class TestPromptDoesNotLeakThePrice:
    def test_the_prompt_asks_the_model_to_search(self):
        """Without this instruction the model answers from memory."""
        from pathlib import Path

        text = Path(debate.__file__).read_text(encoding="utf-8")
        assert "Search for current" in text

    def test_no_market_price_is_interpolated_into_the_prompt(self):
        """Anchoring destroys the only measurement that matters."""
        from pathlib import Path

        text = Path(debate.__file__).read_text(encoding="utf-8")
        prompt_region = text[text.index('prompt = f"""') : text.index("OUTPUT RULES")]
        assert "kalshi_price" not in prompt_region
        assert "Current Kalshi Price" not in prompt_region
