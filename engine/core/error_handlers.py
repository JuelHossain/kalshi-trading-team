"""
Convenience Error Handlers for Ghost Engine
Common error patterns and helper functions.
"""
from typing import Any

from core.error_codes import ErrorDomain, ErrorSeverity


async def handle_ai_unavailable(dispatcher, agent_name: str, context: dict = None) -> Any:
    """Handle AI service unavailable error"""
    return await dispatcher.dispatch(
        code="INTELLIGENCE_AI_UNAVAILABLE",
        severity=ErrorSeverity.HIGH,
        domain=ErrorDomain.INTELLIGENCE,
        context=context or {},
        hint="Check GEMINI_API_KEY in .env file"
    )


async def handle_api_error(dispatcher, status_code: int, context: dict = None) -> Any:
    """Handle API error with status code"""
    if status_code == 429:
        return await dispatcher.dispatch(
            code="NETWORK_RATE_LIMIT",
            severity=ErrorSeverity.HIGH,
            domain=ErrorDomain.NETWORK,
            context=context or {}
        )
    if 500 <= status_code <= 504:
        return await dispatcher.dispatch(
            code="NETWORK_SERVER_ERROR",
            severity=ErrorSeverity.MEDIUM,
            domain=ErrorDomain.NETWORK,
            context=context or {}
        )
    return await dispatcher.dispatch(
        code="NETWORK_CONNECTION_FAILED",
        severity=ErrorSeverity.HIGH,
        domain=ErrorDomain.NETWORK,
        context=context or {}
    )


async def handle_trade_error(dispatcher, error_type: str, context: dict = None) -> Any:
    """Handle common trading errors"""
    error_map = {
        "insufficient_funds": "TRADE_INSUFFICIENT_FUNDS",
        "kill_switch": "TRADE_KILL_SWITCH",
        "invalid_ticker": "TRADE_INVALID_TICKER",
        "order_failed": "TRADE_ORDER_FAILED",
        "hard_floor": "TRADE_HARD_FLOOR",
    }

    code = error_map.get(error_type, "TRADE_ORDER_FAILED")
    return await dispatcher.dispatch(
        code=code,
        severity=ErrorSeverity.HIGH,
        domain=ErrorDomain.TRADING,
        context=context or {}
    )


async def handle_data_error(dispatcher, error_type: str, context: dict = None) -> Any:
    """Handle common data errors"""
    error_map = {
        "queue_empty": "DATA_QUEUE_EMPTY",
        "validation_failed": "DATA_VALIDATION_FAILED",
        "push_failed": "DATA_PUSH_FAILED",
    }

    code = error_map.get(error_type, "DATA_VALIDATION_FAILED")
    return await dispatcher.dispatch(
        code=code,
        severity=ErrorSeverity.MEDIUM,
        domain=ErrorDomain.DATA,
        context=context or {}
    )
