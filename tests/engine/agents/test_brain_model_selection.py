"""GEMINI_MODEL must be used as set, never silently swapped for a dead model.

BrainAgent used to rewrite any GEMINI_MODEL containing "gemini-2.5" to
gemini-2.0-flash-exp as a "defensive fix". get_default_models's own comment
explains what that was defending against: gemini-2.0-flash-exp 404'd and was
removed from the list for being unreachable. gemini-2.5-flash and
gemini-2.5-pro are both still in that same list as valid choices -- so
setting either one silently sent the Brain to the one model already known to
be dead, guaranteeing every primary call failed and fell back to OpenRouter,
with nothing in the logs pointing at the real cause.
"""

import os
from unittest.mock import patch

import pytest
from agents.brain import BrainAgent


def _brain(gemini_model_env: str | None):
    env = {"GEMINI_MODEL": gemini_model_env} if gemini_model_env else {}
    with patch.dict(os.environ, env, clear=True):
        return BrainAgent(agent_id=1, bus=None)


@pytest.mark.parametrize(
    "requested",
    ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.5-flash-lite"],
)
def test_gemini_2_5_models_are_not_downgraded(requested):
    brain = _brain(requested)
    assert brain.gemini_model == requested


def test_gemini_2_0_flash_exp_is_never_chosen_as_a_stand_in():
    """The old downgrade target is dead; nothing should ever land on it silently."""
    for requested in ["gemini-2.5-flash", "gemini-2.5-pro", None]:
        assert _brain(requested).gemini_model != "gemini-2.0-flash-exp"


def test_an_arbitrary_model_name_passes_through_unchanged():
    brain = _brain("some-future-model-name")
    assert brain.gemini_model == "some-future-model-name"


def test_no_env_var_falls_back_to_the_default_list():
    from core.ai_utils import get_default_models

    brain = _brain(None)
    assert brain.gemini_model in get_default_models()
