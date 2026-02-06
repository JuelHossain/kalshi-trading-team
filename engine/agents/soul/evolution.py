"""
Instruction Evolution Logic for Soul Agent
Self-optimization through AI-generated trading instructions.
"""
import asyncio


async def generate_with_fallback(client, ai_client, prompt: str, log_callback) -> str | None:
    """Try generating content with fallback models."""
    # Priority: 3.0 Pro -> 1.5 Flash
    models = ["gemini-3-pro-preview", "gemini-1.5-flash"]

    for model in models:
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: client.models.generate_content(
                    model=model,
                    contents=prompt
                )
            )
            if response and response.text:
                return response.text
        except Exception as e:
            await log_callback(f"Model {model} failed: {e}", level="WARN")
            continue

    await log_callback("All Gemini models failed. Attempting OpenRouter Fallback...", level="WARN")
    return await ai_client._call_openrouter(prompt) if ai_client else None


async def evolve_instructions(
    client,
    ai_client,
    trading_instructions: str,
    strengths_list: list,
    mistakes_log: list,
    log_callback
) -> str:
    """
    Use Gemini to rewrite trading instructions based on history.

    Args:
        client: Gemini client instance
        ai_client: Fallback AI client
        trading_instructions: Current trading instructions
        strengths_list: List of successful trades
        mistakes_log: List of failed trades
        log_callback: Async function for logging

    Returns:
        Updated trading instructions or None if failed
    """
    if not client:
        await log_callback("Gemini unavailable. Using default instructions.")
        return None

    prompt = f"""You are an AI trading strategist. Based on the following recent performance:

WINS: {strengths_list[-5:] if strengths_list else 'None yet'}
LOSSES: {mistakes_log[-5:] if mistakes_log else 'None yet'}

Write a concise set of 5 trading rules to maximize wins and avoid losses. Be specific."""

    try:
        response_text = await generate_with_fallback(client, ai_client, prompt, log_callback)
        if response_text:
            await log_callback("Trading instructions evolved via Gemini.")
            return response_text
        await log_callback("Evolution failed: All models failed.", level="ERROR")
        return None
    except Exception as e:
        await log_callback(f"Evolution failed: {str(e)[:50]}", level="ERROR")
        return None
