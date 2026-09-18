"""
Shared AI Utilities for Agents
Centralizes Gemini initialization and AI client setup.
"""

import os

from core.ai_client import AIClient
from core.bus import EventBus
from core.shared_utils import fire_and_forget

try:
    from google import genai

    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


def initialize_gemini_client(log_callback=None, bus: EventBus = None) -> tuple:
    """
    Initialize Gemini client with OpenRouter fallback.

    Args:
        log_callback: Async function for logging
        bus: EventBus instance

    Returns:
        Tuple of (gemini_client, ai_client, gemini_model, GEMINI_AVAILABLE)
    """
    if not GEMINI_AVAILABLE:
        return (None, None, None, False)

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        if log_callback:
            fire_and_forget(log_callback("Gemini API key not found. AI features disabled."))
        return (None, None, None, False)

    try:
        # Retry transient failures (the SDK default is a single attempt, and
        # its retry codes cover 408/429/5xx). One 429 used to veto the market
        # -- or, before the Brain stopped falling back, hand it to an
        # ungrounded model.
        from google.genai import types as genai_types

        client = genai.Client(
            api_key=api_key,
            http_options=genai_types.HttpOptions(
                # The SDK default is no timeout at all: a request the server
                # accepts and never answers blocked the Brain's only
                # queue-draining loop forever (reproduced against a silent
                # socket). Timeouts are retried like any transient failure.
                timeout=45_000,  # ms
                retry_options=genai_types.HttpRetryOptions(
                    attempts=3, initial_delay=1.0, max_delay=8.0
                ),
            ),
        )
        openrouter_key = os.environ.get("OPENROUTER_API_KEY")

        # Initialize AI client with OpenRouter fallback
        ai_client = AIClient(
            openrouter_key=openrouter_key,
            log_callback=lambda msg, level="INFO": (
                fire_and_forget(log_callback(msg, level=level)) if log_callback else None
            ),
            bus=bus,
        )

        # Default model
        gemini_model = get_default_models()[0]

        return (client, ai_client, gemini_model, True)

    except Exception as e:
        if log_callback:
            fire_and_forget(log_callback(f"Gemini initialization failed: {e}", level="ERROR"))
        return (None, None, None, False)


def get_default_models() -> list[str]:
    """Get list of Gemini models to try (in order of preference)."""
    # Verified against GET /v1beta/models. Every id in the previous list
    # 404'd, including the gemini-2.0-flash-exp used as the default below,
    # so the Brain could not reach a model at all. The *-latest aliases sit
    # last as a rot-resistant floor: they follow Google's current release
    # even after the pinned ids above are retired.
    return [
        "gemini-3.8-flash",
        "gemini-2.5-flash",
        "gemini-2.5-pro",
        "gemini-flash-latest",
        "gemini-pro-latest",
    ]
