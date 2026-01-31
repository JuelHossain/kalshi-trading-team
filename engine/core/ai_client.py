"""
Shared AI client with OpenRouter fallback logic.
Eliminates 84+ lines of duplicate code from brain.py and soul.py.
"""

import asyncio
from typing import Any

import aiohttp


class AIClient:
    """
    Unified AI client with automatic fallback to OpenRouter.
    Supports Gemini with OpenRouter fallback when primary fails.
    """

    # OpenRouter model priority (high-end free models)
    OPENROUTER_MODELS = [
        "tngtech/deepseek-r1t2-chimera:free",      # 671B - WORKS!
        "deepseek/deepseek-r1-0528:free",          # 671B
        "openai/gpt-oss-120b:free",                # 117B - OpenAI's latest
        "meta-llama/llama-3.3-70b-instruct:free",  # 70B - Meta's best
        "google/gemma-3-27b:free",                 # 27B - Google open model
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

    async def _call_openrouter(self, prompt: str) -> str | None:
        """
        Fallback to OpenRouter if primary Google API fails.

        Args:
            prompt: The prompt to send to OpenRouter

        Returns:
            Generated text or None if all models fail
        """
        if not self.openrouter_key:
            await self._log("OpenRouter Fallback Skipped: No API Key found.", "WARN")
            return None

        headers = {
            "Authorization": f"Bearer {self.openrouter_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://kalshi-trading.com",
            "X-Title": "Kalshi Trading Engine"
        }

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
                            await self._log(f"OpenRouter Fallback ({model}) SUCCESS.")
                            return content
                        error_text = await resp.text()
                        await self._log(
                            f"OpenRouter Fallback ({model}) Failed ({resp.status}): {error_text[:100]}",
                            "WARN"
                        )
                except Exception as e:
                    await self._log(f"OpenRouter Connection Error ({model}): {e}", "WARN")

        # All models failed - publish fatal error
        await self._log("ALL AI SERVICES FAILED (Gemini + OpenRouter).", "ERROR")
        if self._bus:
            from agents.base import BaseAgent
            # Publish fatal error
            pass  # Bus publishing handled by caller

        return None
