"""Back-pressure between the agents.

Queue caps and restock rules are read from `core.constants` at call time,
not captured as defaults, so a limit changed from the dashboard applies to
the next check.
"""

from typing import TYPE_CHECKING

from core import constants

if TYPE_CHECKING:
    from core.synapse import Synapse


async def check_execution_queue_limit(
    synapse: "Synapse", limit: int | None = None
) -> tuple[bool, int]:
    """Whether the execution queue is at its cap. Returns (at_limit, size)."""
    if not synapse:
        return False, 0
    cap = constants.MAX_EXECUTION_QUEUE_SIZE if limit is None else limit
    size = await synapse.executions.size()
    return size >= cap, size


async def check_opportunity_queue_limit(
    synapse: "Synapse", limit: int | None = None
) -> tuple[bool, int]:
    """Whether the opportunity queue is at its cap. Returns (at_limit, size)."""
    if not synapse:
        return False, 0
    cap = constants.MAX_OPPORTUNITY_QUEUE_SIZE if limit is None else limit
    size = await synapse.opportunities.size()
    return size >= cap, size


async def should_pause_processing(synapse: "Synapse") -> bool:
    """The Brain pauses while the Hand's queue is full."""
    exec_at_limit, _ = await check_execution_queue_limit(synapse)
    return exec_at_limit


async def should_restock(
    synapse: "Synapse",
    dumped_count: int,
    last_restock_time: float,
    current_time: float,
    veto_threshold: int | None = None,
    cooldown_seconds: float | None = None,
) -> bool:
    """Whether the Brain should ask Senses for fresh markets.

    Requires enough consecutive vetoes, an execution queue with room, and
    the cooldown since the last restock to have passed.
    """
    threshold = constants.RESTOCK_THRESHOLD_VETO_COUNT if veto_threshold is None else veto_threshold
    cooldown = constants.RESTOCK_COOLDOWN_SECONDS if cooldown_seconds is None else cooldown_seconds

    if dumped_count < threshold:
        return False

    exec_at_limit, _ = await check_execution_queue_limit(synapse)
    if exec_at_limit:
        return False

    return not (current_time - last_restock_time) < cooldown
