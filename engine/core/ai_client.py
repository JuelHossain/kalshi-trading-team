"""
Shared AI client with OpenRouter fallback logic.
Eliminates 84+ lines of duplicate code from brain.py and soul.py.
"""

import inspect
from typing import Any

import aiohttp


class AIClient:
    """
    Unified AI client with automatic fallback to OpenRouter.
    Supports Gemini with OpenRouter fallback when primary fails.
    """

    # OpenRouter free-tier model ids, verified against GET /api/v1/models.
    # The previous list 404'd in its entirety -- the free tier churns, so
    # re-check this rather than assuming a failure here is a key problem.
    OPENROUTER_MODELS = [
        "nvidia/nemotron-3-super-120b-a12b:free",
        "nvidia/nemotron-3.5-lightning:free",
    ]

    def __init__(
        self,
        openrouter_key: str | None = None,
        log_callback: Any = None,
        bus: Any = None
    ):
        """
        Initialize the AI client.

        Args:
            openrouter_key: OpenRouter API key (from env)
            log_callback: Async function to call for logging
            bus: EventBus for publishing system events
        """
        self.openrouter_key = openrouter_key
        self._log = log_callback or (lambda msg, level="INFO": None)
        self._bus = bus

    async def _emit(self, message: str, level: str = "INFO") -> None:
        """Log without assuming the callback returns something awaitable.

        Callers supply anything from a coroutine function to the shim in
        ai_utils, which wraps fire_and_forget and so returns None. Awaiting
        that raised "object NoneType can't be used in 'await' expression" on
        every OpenRouter branch that logs -- and those are all failure
        branches, so a recoverable model outage surfaced as an unrelated
        TypeError and tripped the pre-flight lockdown.

        Logging must never be what breaks the caller, so failures here are
        swallowed.
        """
        try:
            result = self._log(message, level)
            if inspect.isawaitable(result):
                await result
        except Exception:  # noqa: BLE001 - logging must not raise
            pass

    async def _call_openrouter(self, prompt: str) -> str | None:
        """
        Fallback to OpenRouter if primary Google API fails.

        Args:
            prompt: The prompt to send to OpenRouter

        Returns:
            Generated text or raises exception if all models fail

        Raises:
            ValueError: If OpenRouter API key is not configured
            RuntimeError: If all OpenRouter models fail
        """
        if not self.openrouter_key:
            await self._emit("OpenRouter API key not configured", "ERROR")
            raise ValueError("OpenRouter API key not configured. Set OPENROUTER_API_KEY in environment.")

        headers = {
            "Authorization": f"Bearer {self.openrouter_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://kalshi-trading.com",
            "X-Title": "Kalshi Trading Engine"
        }

        errors = []
        async with aiohttp.ClientSession() as session:
            for model in self.OPENROUTER_MODELS:
                data = {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}]
                }
                try:
                    async with session.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers=headers,
                        json=data
                    ) as resp:
                        if resp.status == 200:
                            result = await resp.json()
                            content = result["choices"][0]["message"]["content"]
                            await self._emit(f"OpenRouter ({model}) SUCCESS")
                            return content
                        error_text = await resp.text()
                        error_msg = f"Model {model} failed with status {resp.status}: {error_text[:100]}"
                        errors.append(error_msg)
                        await self._emit(error_msg, "WARN")
                except Exception as e:
                    error_msg = f"OpenRouter connection error for {model}: {e}"
                    errors.append(error_msg)
                    await self._emit(error_msg, "WARN")

        # All models failed - raise error instead of returning None
        error_summary = "; ".join(errors)
        await self._emit(f"ALL AI SERVICES FAILED: {error_summary}", "ERROR")
        raise RuntimeError(f"All OpenRouter models failed: {error_summary}")
