"""
Error Code Definitions for Ghost Engine
Standardized error codes with messages and hints.
"""
from enum import Enum


class ErrorSeverity(Enum):
    """Error severity levels"""
    CRITICAL = 5  # System-wide failure, requires immediate intervention
    HIGH = 4      # Component failure, degrades service
    MEDIUM = 3    # Feature failure, workarounds available
    LOW = 2       # Minor issue, no impact on operations
    INFO = 1      # Informational, no error


class ErrorDomain(Enum):
    """Error domains by component"""
    NETWORK = "NETWORK"         # API connections, timeouts
    TRADING = "TRADING"         # Order execution, vault
    INTELLIGENCE = "INTELLIGENCE"  # AI services, Gemini
    DATA = "DATA"               # Queues, database, validation
    AUTH = "AUTH"               # Authentication, credentials
    CONFIG = "CONFIG"           # Environment, setup
    SYSTEM = "SYSTEM"           # General system errors


class ErrorCodes:
    """Standardized error codes with messages and hints"""

    # Network Errors (NETWORK_xxx)
    NETWORK_TIMEOUT = ("NETWORK_TIMEOUT", "API request timeout", "Check network connection")
    NETWORK_RATE_LIMIT = ("NETWORK_RATE_LIMIT", "API rate limit exceeded", "Wait before retrying")
    NETWORK_CONNECTION_FAILED = ("NETWORK_CONNECTION_FAILED", "Failed to connect to API", "Verify API credentials")
    NETWORK_SERVER_ERROR = ("NETWORK_SERVER_ERROR", "API server error", "Try again later")

    # Trading Errors (TRADING_xxx)
    TRADE_INSUFFICIENT_FUNDS = ("TRADE_INSUFFICIENT_FUNDS", "Insufficient vault balance", "Wait for order settlements")
    TRADE_KILL_SWITCH = ("TRADE_KILL_SWITCH", "Kill switch activated", "Manual intervention required")
    TRADE_INVALID_TICKER = ("TRADE_INVALID_TICKER", "Invalid market ticker", "Verify ticker symbol")
    TRADE_ORDER_FAILED = ("TRADE_ORDER_FAILED", "Order placement failed", "Check order parameters")
    TRADE_HARD_FLOOR = ("TRADE_HARD_FLOOR", "Balance below hard floor", "Emergency lockdown active")

    # Intelligence Errors (INTELLIGENCE_xxx)
    INTELLIGENCE_AI_UNAVAILABLE = ("INTELLIGENCE_AI_UNAVAILABLE", "AI service unavailable", "Check API key configuration")
    INTELLIGENCE_DEBATE_FAILED = ("INTELLIGENCE_DEBATE_FAILED", "AI debate failed", "System will veto trade")
    INTELLIGENCE_PARSE_ERROR = ("INTELLIGENCE_PARSE_ERROR", "Failed to parse AI response", "Response format invalid")
    INTELLIGENCE_TIMEOUT = ("INTELLIGENCE_TIMEOUT", "AI request timeout", "Service may be overloaded")

    # Data Errors (DATA_xxx)
    DATA_QUEUE_EMPTY = ("DATA_QUEUE_EMPTY", "No data in queue", "Waiting for new opportunities")
    DATA_VALIDATION_FAILED = ("DATA_VALIDATION_FAILED", "Data validation failed", "Check data format")
    DATA_PUSH_FAILED = ("DATA_PUSH_FAILED", "Failed to queue data", "Queue may be full")

    # Auth Errors (AUTH_xxx)
    AUTH_INVALID_KEY = ("AUTH_INVALID_KEY", "Invalid API credentials", "Check .env configuration")
    AUTH_MISSING_KEY = ("AUTH_MISSING_KEY", "API key not configured", "Set GEMINI_API_KEY in .env")

    # Config Errors (CONFIG_xxx)
    CONFIG_MISSING_ENV = ("CONFIG_MISSING_ENV", "Environment variable missing", "Check .env file")
    CONFIG_INVALID_VALUE = ("CONFIG_INVALID_VALUE", "Invalid configuration value", "Check config file")

    # System Errors (SYSTEM_xxx)
    SYSTEM_INIT_FAILED = ("SYSTEM_INIT_FAILED", "System initialization failed", "Check agent dependencies")
    SYSTEM_EVENT_BUS_FAILED = ("SYSTEM_EVENT_BUS_FAILED", "Event bus error", "Check agent subscriptions")


# Windows-safe terminal colors
class Colors:
    """Terminal color codes (Windows-safe)"""
    RED = "\033[91m"      # CRITICAL
    YELLOW = "\033[93m"    # HIGH
    ORANGE = "\033[38;5;208m"  # MEDIUM
    BLUE = "\033[94m"      # LOW
    GRAY = "\033[90m"      # INFO
    GREEN = "\033[92m"     # SUCCESS
    RESET = "\033[0m"
    BOLD = "\033[1m"
