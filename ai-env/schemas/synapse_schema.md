# Synapse Persistent Schema

- **Database**: `engine/ghost_memory.db`

## 1. Opportunities (`queue_opportunities`)
Pushed by **SENSES**, consumed by **BRAIN**.

```json
{
  "id": "uuid-v4",
  "ticker": "STRING",
  "market_data": {
    "ticker": "STRING",
    "title": "STRING",
    "subtitle": "STRING",
    "yes_price": "INT (cents)",
    "no_price": "INT (cents)",
    "volume": "INT",
    "expiration": "ISO-TIMESTAMP",
    "raw_response": "DICT"
  },
  "source": "SENSES",
  "priority": "INT (Higher = Faster)",
  "timestamp": "ISO-TIMESTAMP"
}
```

## 2. Execution Signals (`queue_executions`)
Pushed by **BRAIN**, consumed by **HAND**.

```json
{
  "id": "uuid-v4",
  "target_opportunity": "OPPORTUNITY_MODEL",
  "action": "BUY",
  "side": "YES | NO",
  "confidence": "FLOAT (0.0 - 1.0)",
  "monte_carlo_ev": "FLOAT",
  "reasoning": "STRING",
  "suggested_count": "INT",
  "status": "PENDING | EXECUTED | FAILED | CANCELLED",
  "timestamp": "ISO-TIMESTAMP"
}
```

- **Persistence Rule**: Every decision by Brain must be committed to `queue_executions` before triggering the Hand agent.---

*Last schema evolution: 2026-01-29 20:34*
*Triggered by changes in: `engine/core/bus.py`, `engine/core/network.py`, `engine/core/synapse.py`, `engine/core/vault.py`*
*Triggered by changes in: `engine/core/bus.py`, `engine/core/network.py`, `engine/core/synapse.py`, `engine/core/vault.py`*
*Triggered by changes in: `engine/core/bus.py`, `engine/core/network.py`, `engine/core/synapse.py`, `engine/core/vault.py`*
