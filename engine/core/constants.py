"""
Centralized constants for the Ghost Engine.
Eliminates duplication across main.py, gateway.py, and other modules.
"""

# ==============================================================================
# AGENT IDENTIFIERS
# ==============================================================================

from core.shared_utils import get_env_float

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
BRAIN_CONFIDENCE_THRESHOLD = 0.85  # 85% minimum AI confidence in its estimate

# Minimum edge (estimated probability minus contract price) required to trade.
# Replaces BRAIN_MAX_VARIANCE, which could never bind: the variance of a binary
# outcome is p(1-p), whose maximum is exactly the 0.25 the veto tested against.
# Edge is the quantity that actually decides whether a trade is worth taking,
# and a floor on it keeps the engine out of thin edges that the spread eats.
# Overridable so the execution path can be exercised on demand. With the
# floor at its default the Brain vetoes nearly everything -- correct, but it
# means an untested order path can sit behind the veto indefinitely looking
# fine. Lower it in paper mode to prove the Hand actually fills.
BRAIN_MIN_EDGE = get_env_float("BRAIN_MIN_EDGE", 0.05)

# How long a queued opportunity may wait before the Brain refuses it.
#
# This measures queue wait, not market movement: the Hand re-reads the live
# orderbook before any order, so execution freshness is guarded there. What
# this protects against is analysing a snapshot from a different cycle.
#
# It was a hardcoded 60s, tuned when an estimate took ~2s. Search-grounded
# estimates take ~15s, so in a batch of ten the fifth item onward was
# already "stale" -- observed live at 65-74s -- and half of every batch was
# discarded unanalysed. Ten grounded calls plus slack is the floor here.
BRAIN_STALE_OPPORTUNITY_SECONDS = get_env_float("BRAIN_STALE_OPPORTUNITY_SECONDS", 300.0)

# How many independent estimates to draw per market. One opinion has no
# uncertainty attached to it; several do. Set to 1 to disable sampling and pay
# a single API call per market.
BRAIN_ESTIMATE_SAMPLES = 3

# Reject when independent estimates disagree by more than this. This is the
# risk signal the variance veto was reaching for and could never provide:
# unlike p(1-p), disagreement varies independently of the probability, so it
# can actually bind. Wide disagreement means the model does not know, which is
# different from -- and more dangerous than -- believing the odds are even.
BRAIN_MAX_DISAGREEMENT = 0.20


# Hand Agent
HAND_MAX_STAKE_CENTS = 7500  # $75 max per trade

# --- Exit policy -------------------------------------------------------------
# The engine can close a position; these decide when it should.
#
# Holding every contract to settlement is defensible for binaries -- they
# resolve to 0 or 100, so time favours a correct forecast. But a contract
# bought at 60c that has drifted to 5c is near-certainly lost, and holding it
# converts "near-certainly" into "certainly" while the capital sits idle.

# Close when the price has fallen this far below what was paid.
HAND_STOP_LOSS_PCT = 0.50

# Close when the price has captured this much of the distance from entry to
# 100 -- trading the last of the upside for certainty.
HAND_TAKE_PROFIT_PCT = 0.80

# Close a losing position this many hours before expiry. A winning one is left
# to settle, since settlement pays 100 and a thin pre-expiry book does not.
HAND_EXIT_BEFORE_EXPIRY_HOURS = 2.0

# Fraction of full Kelly to stake. Full Kelly maximises long-run growth but is
# famously violent; a quarter is the usual conservative choice and costs little
# expected growth for a large reduction in drawdown.
HAND_KELLY_FRACTION = 0.25

# ==============================================================================
# VAULT SAFETY
# ==============================================================================

# Balance below which the engine refuses to trade and locks down.
# Single source of truth: RecursiveVault and engine/config.py both read this.
# It was previously written out separately in each, so changing one silently
# left the others disagreeing about a safety limit.
HARD_FLOOR_CENTS = 25500  # $255.00
HAND_PROFIT_LOCK_THRESHOLD = 5000  # $50 profit triggers principal lock
