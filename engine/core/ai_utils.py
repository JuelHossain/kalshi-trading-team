"""
Shared AI Utilities for Agents
Centralizes Gemini initialization and AI client setup.
"""
import asyncio
import os

from core.ai_client import AIClient
from core.bus import EventBus

try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


def initialize_gemini_client(
    log_callback=None,
    bus: EventBus = None
) -> tuple:
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
            asyncio.create_task(log_callback("Gemini API key not found. AI features disabled."))
        return (None, None, None, False)

    try:
        client = genai.Client(api_key=api_key)
        openrouter_key = os.environ.get("OPENROUTER_API_KEY")

        # Initialize AI client with OpenRouter fallback
        ai_client = AIClient(
            openrouter_key=openrouter_key,
            log_callback=lambda msg, level="INFO": asyncio.create_task(
                log_callback(msg, level=level)
            ) if log_callback else None,
            bus=bus
        )

        # Default model
        gemini_model = "gemini-2.0-flash-exp"

        return (client, ai_client, gemini_model, True)

    except Exception as e:
        if log_callback:
            asyncio.create_task(log_callback(f"Gemini initialization failed: {e}", level="ERROR"))
        return (None, None, None, False)


def get_default_models() -> list[str]:
    """Get list of Gemini models to try (in order of preference)."""
    return [
        "gemini-3-flash-preview",
        "gemini-3-pro-preview",
        "gemini-2.0-flash-thinking-exp-01-21",
        "gemini-2.0-pro-exp-02-05",
        "gemini-2.0-flash-exp",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
    ]
