"""
Centralized constants for the Ghost Engine.
Eliminates duplication across main.py, gateway.py, and other modules.
"""

# ==============================================================================
# AGENT IDENTIFIERS
# ==============================================================================

AGENT_ID_SOUL = 1
AGENT_ID_SENSES = 2
AGENT_ID_BRAIN = 3
AGENT_ID_HAND = 4
AGENT_ID_GATEWAY = 5

# Agent name to ID mapping
AGENT_NAME_TO_ID = {
    "SOUL": AGENT_ID_SOUL,
    "SENSES": AGENT_ID_SENSES,
    "BRAIN": AGENT_ID_BRAIN,
    "HAND": AGENT_ID_HAND,
    "GATEWAY": AGENT_ID_GATEWAY,
}

# ==============================================================================
# PHASE MAPPINGS
# ==============================================================================

# Agent to Phase mapping (mirrors shared/constants.ts)
# Used for visualizer and event formatting
AGENT_TO_PHASE = {
    AGENT_ID_SOUL: 1,      # Phase 1: System Init
    AGENT_ID_SENSES: 2,    # Phase 2: Surveillance
    AGENT_ID_BRAIN: 3,     # Phase 3: Intelligence
    AGENT_ID_HAND: 4,      # Phase 4: Execution
    AGENT_ID_GATEWAY: 4,   # Phase 4: Gateway (part of Hand output)
}

# Extended phase mapping (includes all 14 agents from original design)
FULL_AGENT_TO_PHASE = {
    1: 0,
    11: 0,  # Phase 0: System Init
    2: 1,
    3: 1,
    7: 1,  # Phase 1: Surveillance
    4: 2,
    5: 2,
    6: 2,  # Phase 2: Intelligence
    8: 3,  # Phase 3: Execution
    9: 4,
    10: 4,  # Phase 4: Accounting
    12: 5,
    14: 5,  # Phase 5: Protection
    13: 13,  # Intervention
}

# ==============================================================================
# FLOW CONTROL LIMITS
# ==============================================================================

# Maximum queue sizes to prevent overload
MAX_EXECUTION_QUEUE_SIZE = 10
MAX_OPPORTUNITY_QUEUE_SIZE = 20

# Restock triggers
RESTOCK_THRESHOLD_VETO_COUNT = 5  # Request restock after 5 vetoes
RESTOCK_COOLDOWN_SECONDS = 60     # Minimum time between restocks

# ==============================================================================
# CYCLE CONFIGURATION
# ==============================================================================

MIN_CYCLE_INTERVAL_SECONDS = 30

# ==============================================================================
# AGENT-SPECIFIC CONSTANTS
# ==============================================================================

# Senses Agent
SENSES_MIN_LIQUIDITY = 1000  # $10 minimum liquidity
SENSES_STOCK_BUFFER_SIZE = 30  # Total markets to pull from Kalshi
SENSES_QUEUE_BATCH_SIZE = 10   # Markets to queue at once

# Brain Agent
BRAIN_CONFIDENCE_THRESHOLD = 0.85  # 85% minimum confidence
BRAIN_SIMULATION_ITERATIONS = 10000
BRAIN_MAX_VARIANCE = 0.25  # Maximum acceptable variance

# Hand Agent
HAND_MAX_STAKE_CENTS = 7500  # $75 max per trade
HAND_PROFIT_LOCK_THRESHOLD = 5000  # $50 profit triggers principal lock
