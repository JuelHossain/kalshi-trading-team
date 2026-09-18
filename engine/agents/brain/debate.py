"""
AI Debate Logic for Brain Agent
Multi-persona debate using Gemini with OpenRouter fallback.
"""

import asyncio
import json
import os
from typing import Any

from core.error_dispatcher import ErrorSeverity
from core.logger import get_logger

# Google Search grounding for the probability estimate. On by default:
# without it the model answers from training data, which on a dated event is
# guesswork wearing a confidence score.
#
# Measured on the same NFL market, same model, same prompt:
#   ungrounded  p=0.38 confidence=45  "Assuming the matchup takes place..."
#   grounded    p=0.25 confidence=85  "Consensus betting markets list the
#                                      Rams as ~7.5-point home favorites"
# The real Kalshi price was 0.26. Ungrounded estimates sat below the 85%
# confidence threshold, so the engine vetoed everything and never traded.
#
# Set BRAIN_SEARCH_GROUNDING=false to get the old behaviour for comparison.
GROUNDING_ENABLED = os.getenv("BRAIN_SEARCH_GROUNDING", "true").strip().lower() not in (
    "false",
    "0",
    "no",
)


def build_grounding_config():
    """Return a generate_content config enabling Google Search, or None.

    None means "call the model without a config", which is the ungrounded
    path. Returning None on ImportError keeps an SDK change from taking the
    Brain offline -- a degraded estimate still beats no estimate, and the
    confidence threshold is what stops a bad one reaching the Hand.
    """
    # Read live so the dashboard toggle applies to the next estimate;
    # GROUNDING_ENABLED above records what the process booted with.
    from core.settings import settings

    if not settings.get_bool("BRAIN_SEARCH_GROUNDING"):
        return None
    try:
        from google.genai import types
    except ImportError:
        return None
    return types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())])


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
        "critic": "CRITIC: Argue against this trade.",
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


def _normalise_confidence(raw: Any) -> float:
    """Return confidence as a 0-1 fraction, accepting either scale.

    The prompt asks for an integer 0-100, but models frequently answer 0.85
    instead of 85. The old parser divided unconditionally by 100, turning 0.85
    into 0.0085 -- below every threshold, so the bot silently stopped trading
    with no error anywhere.

    A value at or below 1.0 is read as a fraction, above that as a percentage.
    Anything unparseable or out of range is treated as no confidence, which
    vetoes the trade rather than guessing.
    """
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return 0.0

    if value < 0:
        return 0.0
    if value <= 1.0:
        return value
    if value <= 100.0:
        return value / 100.0
    return 0.0


def _validate_probability(raw: Any) -> float | None:
    """Return a probability in [0, 1], or None if the model gave something else.

    None propagates to the caller's veto rather than silently defaulting to
    0.5, which would have the bot trade on a coin flip it never estimated.
    """
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None

    return value if 0.0 <= value <= 1.0 else None


async def run_debate(
    opportunity: dict,
    client: Any,
    gemini_model: str,
    personas: dict,
    trading_instructions: str,
    ai_client: Any,
    log_callback: Any,
    log_error_callback: Any,
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
            # MEDIUM, as at every per-sample failure below: each returns
            # confidence 0, which vetoes this one market, and the ensemble
            # tolerates a failed sample. At HIGH, one truncated reply from one
            # sample latched the error box and halted the whole engine -- seen
            # live 2026-09-18, on a ticker the other two samples still scored.
            severity=ErrorSeverity.MEDIUM,
            context={"opportunity": opportunity.get("ticker", "UNKNOWN")},
        )
        # Return zero confidence to trigger veto
        return {
            "confidence": 0.0,
            "reasoning": "AI service unavailable - trade rejected for safety",
            "estimated_probability": None,
        }

    ticker = opportunity.get("ticker", "UNKNOWN")
    market_data = opportunity.get("market_data", {})
    title = market_data.get("title", ticker)
    subtitle = market_data.get("subtitle", "")

    # The market price is deliberately NOT shown to the model.
    #
    # This prompt previously included "Current Kalshi Price: {x}%" before asking
    # for the true probability. Anchoring is one of the most reliably reproduced
    # effects in language models, so the estimate drifted toward the number it
    # had just been shown -- and the bot's entire edge is the gap between its
    # estimate and that price. Asking the model to beat a number while showing
    # it the number destroys the measurement.
    #
    # Nothing is lost by withholding it: the price never entered the model's
    # arithmetic. EV and sizing are computed in Python from the returned
    # probability and the real book price.

    prompt = f"""You are a forecasting committee estimating the probability of a real-world event.

EVENT: {ticker}
TITLE: {title}
SUBTITLE: {subtitle}

{f"Today's Trading Instructions: {trading_instructions[:500]}" if trading_instructions else ""}

TASK:
Estimate the TRUE probability of this event occurring. Search for current
information about it -- form, injuries, standings, recent reporting, whatever
bears on the outcome -- rather than relying on memory, which may be stale or
may predate the event entirely. You are NOT being shown any market price, and
you should not guess at one -- estimate the event on its merits alone.

1. OPTIMIST: argue why the event is more likely than it first appears.
2. CRITIC: argue why it is less likely than it first appears.
3. JUDGE: weigh both and commit to a single probability.

PERSONAS:
{personas['optimist']}

{personas['critic']}

OUTPUT RULES:
- estimated_probability: a decimal between 0.0 and 1.0
- confidence: an INTEGER from 0 to 100, how sure you are of that estimate

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
            grounding = build_grounding_config()
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: client.models.generate_content(
                    model=gemini_model, contents=prompt, config=grounding
                ),
            )
            text = response.text
        except Exception as e:
            # Fallback: OpenRouter
            await log_callback(
                f"[BRAIN] Primary AI failed ({str(e)[:50]})... Attempting OpenRouter Fallback.",
                level="WARN",
            )
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
                confidence = _normalise_confidence(result.get("confidence"))
                probability = _validate_probability(result.get("estimated_probability"))

                if probability is None:
                    await log_callback(
                        f"Unusable probability from AI for {ticker}: "
                        f"{result.get('estimated_probability')!r} - rejecting",
                        level="WARN",
                    )
                    return {
                        "confidence": 0.0,
                        "reasoning": "AI returned an out-of-range probability - trade rejected",
                        "estimated_probability": None,
                    }

                return {
                    "confidence": confidence,
                    "reasoning": result.get("judge_verdict", ""),
                    "estimated_probability": probability,
                }
            except json.JSONDecodeError as je:
                await log_callback(
                    f"JSON parse error for {ticker}. Response: {text[:200]}", level="ERROR"
                )
                await log_error_callback(
                    code="INTELLIGENCE_PARSE_ERROR",
                    message=f"JSON parsing failed for {ticker}",
                    severity=ErrorSeverity.MEDIUM,
                    context={
                        "ticker": ticker,
                        "error": str(je)[:100],
                        "response_preview": text[:200],
                    },
                    exception=je,
                )
                return {
                    "confidence": 0.0,
                    "reasoning": f"JSON parse error - trade rejected: {str(je)[:50]}",
                    "estimated_probability": None,
                }

        # No JSON found at all
        await log_callback(
            f"No JSON found in AI response for {ticker}. Response: {text[:200]}", level="ERROR"
        )
        await log_error_callback(
            code="INTELLIGENCE_PARSE_ERROR",
            message="No JSON found in AI response",
            severity=ErrorSeverity.MEDIUM,
            context={"ticker": ticker, "response_preview": text[:200]},
        )
        return {
            "confidence": 0.0,
            "reasoning": "Invalid AI response format - trade rejected",
            "estimated_probability": None,
        }

    except json.JSONDecodeError as e:
        await log_callback(f"JSON decode error for {ticker}: {str(e)[:100]}", level="ERROR")
        await log_error_callback(
            code="INTELLIGENCE_PARSE_ERROR",
            message=f"JSON parsing failed for {ticker}",
            severity=ErrorSeverity.MEDIUM,
            context={"ticker": ticker, "error": str(e)[:100]},
            exception=e,
        )
        return {
            "confidence": 0.0,
            "reasoning": f"JSON parse error - trade rejected: {str(e)[:50]}",
            "estimated_probability": None,
        }

    except AttributeError as e:
        await log_error_callback(
            code="INTELLIGENCE_PARSE_ERROR",
            message="AI response format error",
            severity=ErrorSeverity.MEDIUM,
            context={"ticker": ticker, "error": str(e)[:100]},
            exception=e,
        )
        return {
            "confidence": 0.0,
            "reasoning": f"Invalid AI response format - trade rejected: {str(e)[:50]}",
            "estimated_probability": None,
        }

    except ConnectionError as e:
        await log_error_callback(
            code="INTELLIGENCE_TIMEOUT",
            message="AI API connection failed",
            severity=ErrorSeverity.MEDIUM,
            context={"ticker": ticker, "error": str(e)[:100]},
            exception=e,
        )
        await asyncio.sleep(0.5)
        return {
            "confidence": 0.0,
            "reasoning": "AI service unavailable - trade rejected",
            "estimated_probability": None,
        }

    except Exception as e:
        error_type = type(e).__name__
        await log_error_callback(
            code="INTELLIGENCE_DEBATE_FAILED",
            message=f"Debate error ({error_type}) for {ticker}",
            severity=ErrorSeverity.MEDIUM,
            context={"ticker": ticker, "error_type": error_type, "error": str(e)[:100]},
            exception=e,
        )
        await asyncio.sleep(0.5)
        return {
            "confidence": 0.0,
            "reasoning": f"Debate failed ({error_type}) - trade rejected",
            "estimated_probability": None,
        }


async def run_debate_ensemble(samples: int = 1, **kwargs) -> dict:
    """Draw several independent estimates and report how much they disagree.

    A single call gives a probability with no uncertainty attached to it. The
    engine treated that number as fact, and its only risk gate was the variance
    of the outcome -- p(1-p), which is a fixed function of the probability and
    so carries no information the probability does not already carry.

    Sampling the same question repeatedly gives a spread. That spread is a real
    signal: it varies independently of the probability, so it can actually
    reject a trade. Wide disagreement means the model does not know, which is
    different from -- and more dangerous than -- it believing the odds are even.

    Returns the usual debate fields plus:
        disagreement: max estimate minus min estimate, 0.0 for a single sample
        samples:      how many usable estimates were obtained

    The median is used rather than the mean, so one wild draw cannot drag the
    estimate. Confidence is taken as the minimum across samples: if any run was
    unsure, the ensemble is unsure.
    """
    if samples <= 1:
        result = await run_debate(**kwargs)
        result.setdefault("disagreement", 0.0)
        result.setdefault("samples", 1)
        return result

    results = await asyncio.gather(
        *[run_debate(**kwargs) for _ in range(samples)], return_exceptions=True
    )

    usable = [
        r for r in results if isinstance(r, dict) and r.get("estimated_probability") is not None
    ]

    if not usable:
        return {
            "confidence": 0.0,
            "reasoning": "No usable estimate from any sample - trade rejected",
            "estimated_probability": None,
            "disagreement": 1.0,
            "samples": 0,
        }

    probabilities = sorted(r["estimated_probability"] for r in usable)
    middle = len(probabilities) // 2
    median = (
        probabilities[middle]
        if len(probabilities) % 2
        else (probabilities[middle - 1] + probabilities[middle]) / 2
    )

    return {
        "confidence": min(r.get("confidence", 0.0) for r in usable),
        "reasoning": usable[0].get("reasoning", ""),
        "estimated_probability": median,
        "disagreement": probabilities[-1] - probabilities[0],
        "samples": len(usable),
    }
