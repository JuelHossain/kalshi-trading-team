"""
AI Debate Logic for Brain Agent
Multi-persona debate using Gemini with OpenRouter fallback.
"""
import asyncio
import json
import os
from typing import Any

from core.ai_utils import GEMINI_AVAILABLE
from core.error_dispatcher import ErrorSeverity
from core.logger import get_logger


def load_personas(base_path: str = "ai-env/personas") -> dict[str, str]:
    """
    Load character definitions from the centralized ai-env library.

    Args:
        base_path: Base path to personas directory

    Returns:
        Dictionary of persona names to their descriptions
    """
    personas = {
        "optimist": "OPTIMIST: Argue why this is a great opportunity.",
        "critic": "CRITIC: Argue against this trade."
    }

    try:
        opt_path = os.path.join(base_path, "optimist.md")
        cri_path = os.path.join(base_path, "critic.md")

        if os.path.exists(opt_path):
            with open(opt_path) as f:
                personas["optimist"] = f"OPTIMIST: {f.read().strip()}"

        if os.path.exists(cri_path):
            with open(cri_path) as f:
                personas["critic"] = f"CRITIC: {f.read().strip()}"

    except Exception as e:
        get_logger("BRAIN").warning(f"[BRAIN] Persona Load Warning: {e}")
        # Continue with default personas

    return personas


async def run_debate(
    opportunity: dict,
    client: Any,
    gemini_model: str,
    personas: dict,
    trading_instructions: str,
    ai_client: Any,
    log_callback: Any,
    log_error_callback: Any
) -> dict:
    """
    Run multi-persona AI debate using Gemini.

    Args:
        opportunity: Market opportunity data
        client: Gemini client instance
        gemini_model: Model name to use
        personas: Persona descriptions
        trading_instructions: Current trading instructions
        ai_client: Fallback AI client
        log_callback: Async function for logging
        log_error_callback: Async function for error logging

    Returns:
        Dictionary with confidence, reasoning, and estimated_probability
    """
    if not client:
        # Use centralized error system
        await log_error_callback(
            code="INTELLIGENCE_AI_UNAVAILABLE",
            severity=ErrorSeverity.HIGH,
            context={"opportunity": opportunity.get("ticker", "UNKNOWN")}
        )
        # Return zero confidence to trigger veto
        return {
            "confidence": 0.0,
            "reasoning": "AI service unavailable - trade rejected for safety",
            "estimated_probability": None
        }

    ticker = opportunity.get("ticker", "UNKNOWN")
    market_data = opportunity.get("market_data", {})
    title = market_data.get("title", ticker)
    subtitle = market_data.get("subtitle", "")

    kalshi_price = opportunity.get("kalshi_price", 0.5)

    # Check if we have external odds (legacy support)
    has_odds = opportunity.get("vegas_prob") is not None
    odds_context = f"Vegas Probability: {opportunity['vegas_prob']*100:.1f}%" if has_odds else "NO EXTERNAL ODDS AVAILABLE."

    fetched_news = opportunity.get("external_context", "")
    full_context = f"ODDS: {odds_context}\nNEWS/CONTEXT:\n{fetched_news}" if fetched_news else f"ODDS: {odds_context}\n(No news found)"

    prompt = f"""You are a trading committee with two personas debating a market opportunity.

MARKET: {ticker}
TITLE: {title}
SUBTITLE: {subtitle}
Current Kalshi Price: {kalshi_price*100:.1f}%
Context: {full_context}

{f"Today's Trading Instructions: {trading_instructions[:500]}" if trading_instructions else ""}

TASK:
1. Estimate the TRUE probability of this event occurring (0.00 to 1.00) based on your knowledge of the world and the provided Context.
2. Debate the trade at the current price.
3. Explicitly reference the 'NEWS/CONTEXT' in your reasoning if available.

PERSONAS:
{personas['optimist']}

{personas['critic']}

JUDGE: Final verdict based on the debate above.

Respond in JSON format:
{{
  "optimist": "...",
  "critic": "...",
  "judge_verdict": "...",
  "estimated_probability": 0.75,
  "confidence": 85
}}"""

    try:
        try:
            # Primary: Google Gemini API
            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: client.models.generate_content(model=gemini_model, contents=prompt)
            )
            text = response.text
        except Exception as e:
            # Fallback: OpenRouter
            await log_callback(f"[BRAIN] Primary AI failed ({str(e)[:50]})... Attempting OpenRouter Fallback.", level="WARN")
            text = await ai_client._call_openrouter(prompt) if ai_client else None
            if not text:
                raise e

        # Parse response
        import re

        # Extract JSON from response
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match:
            try:
                result = json.loads(json_match.group())
                return {
                    "confidence": result.get("confidence", 50) / 100,
                    "reasoning": result.get("judge_verdict", ""),
                    "estimated_probability": result.get("estimated_probability", 0.5)
                }
            except json.JSONDecodeError as je:
                await log_callback(f"JSON parse error for {ticker}. Response: {text[:200]}", level="ERROR")
                await log_error_callback(
                    code="INTELLIGENCE_PARSE_ERROR",
                    message=f"JSON parsing failed for {ticker}",
                    severity=ErrorSeverity.HIGH,
                    context={"ticker": ticker, "error": str(je)[:100], "response_preview": text[:200]},
                    exception=je
                )
                return {"confidence": 0.0, "reasoning": f"JSON parse error - trade rejected: {str(je)[:50]}", "estimated_probability": None}

        # No JSON found at all
        await log_callback(f"No JSON found in AI response for {ticker}. Response: {text[:200]}", level="ERROR")
        await log_error_callback(
            code="INTELLIGENCE_PARSE_ERROR",
            message="No JSON found in AI response",
            severity=ErrorSeverity.HIGH,
            context={"ticker": ticker, "response_preview": text[:200]}
        )
        return {"confidence": 0.0, "reasoning": "Invalid AI response format - trade rejected", "estimated_probability": None}

    except json.JSONDecodeError as e:
        await log_callback(f"JSON decode error for {ticker}: {str(e)[:100]}", level="ERROR")
        await log_error_callback(
            code="INTELLIGENCE_PARSE_ERROR",
            message=f"JSON parsing failed for {ticker}",
            severity=ErrorSeverity.HIGH,
            context={"ticker": ticker, "error": str(e)[:100]},
            exception=e
        )
        return {"confidence": 0.0, "reasoning": f"JSON parse error - trade rejected: {str(e)[:50]}", "estimated_probability": None}

    except AttributeError as e:
        await log_error_callback(
            code="INTELLIGENCE_PARSE_ERROR",
            message="AI response format error",
            severity=ErrorSeverity.HIGH,
            context={"ticker": ticker, "error": str(e)[:100]},
            exception=e
        )
        return {"confidence": 0.0, "reasoning": f"Invalid AI response format - trade rejected: {str(e)[:50]}", "estimated_probability": None}

    except ConnectionError as e:
        await log_error_callback(
            code="INTELLIGENCE_TIMEOUT",
            message="AI API connection failed",
            severity=ErrorSeverity.HIGH,
            context={"ticker": ticker, "error": str(e)[:100]},
            exception=e
        )
        await asyncio.sleep(0.5)
        return {"confidence": 0.0, "reasoning": "AI service unavailable - trade rejected", "estimated_probability": None}

    except Exception as e:
        error_type = type(e).__name__
        await log_error_callback(
            code="INTELLIGENCE_DEBATE_FAILED",
            message=f"Debate error ({error_type}) for {ticker}",
            severity=ErrorSeverity.HIGH,
            context={"ticker": ticker, "error_type": error_type, "error": str(e)[:100]},
            exception=e
        )
        await asyncio.sleep(0.5)
        return {"confidence": 0.0, "reasoning": f"Debate failed ({error_type}) - trade rejected", "estimated_probability": None}
