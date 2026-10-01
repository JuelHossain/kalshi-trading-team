# Architecture

The engine is four agents on one event bus, with three SQLite-backed queues
between them and a set of capital rules that gate every cycle. This page
describes what is in the tree today; the AI-assistant governance documents
live under [`ai-env/core-docs/`](../../ai-env/core-docs/).

## Agents

| Agent | Package | Subscribes to | Publishes |
|---|---|---|---|
| Soul | `engine/agents/soul/` | `CYCLE_START`, `TRADE_RESULT`, `CYCLE_COMPLETE`, `SYSTEM_CONTROL` | `PREFLIGHT_COMPLETE`, `REQUEST_CYCLE`, `SYSTEM_LOCKDOWN` |
| Senses | `engine/agents/senses/` | `PREFLIGHT_COMPLETE`, `REQUEST_RESTOCK` | `OPPORTUNITY_FOUND`, `OPPORTUNITIES_READY` |
| Brain | `engine/agents/brain/` | (drains the opportunity queue continuously), `SYSTEM_CONTROL` | `SIM_RESULT`, `EXECUTION_SIGNAL`, `REQUEST_RESTOCK` |
| Hand | `engine/agents/hand/` | `EXECUTION_SIGNAL`, `CYCLE_END` | `TRADE_RESULT`, `VAULT_UPDATE` |
| Gateway | `engine/agents/gateway.py` | `SYSTEM_LOG`, `SIM_RESULT`, `SYSTEM_HEALTH`, `SYSTEM_ERROR` | `VAULT_UPDATE`, `SYSTEM_STATE` (its own), never what it relays |

All agents extend `BaseAgent`, which subscribes them to `TICK` and gives
them `log()`, which is itself a `SYSTEM_LOG` publish.

## One cycle

1. `POST /trigger` (or Soul's autopilot) publishes `CYCLE_START`.
2. **Soul** refuses the cycle if the vault is below its hard floor, the kill
   switch is set, or the error box is non-empty. Otherwise it runs pre-flight
   (Kalshi reachable, model reachable) and publishes `PREFLIGHT_COMPLETE`.
3. **Senses** fills a 30-market buffer -- liquid, tightly quoted, closing
   within ten days, excluding combo shards and anything queued recently --
   and pushes 10 onto the opportunity queue.
4. **Brain** pops one at a time. It asks the model for a probability with
   the market price withheld and Google Search grounding on, computes EV and
   edge against the real price, vetoes below the confidence or edge floor,
   records the decision in the ledger, and on approval pushes an execution
   signal.
5. **Hand** re-reads the live orderbook, refuses stacking into a held market
   or thin depth at the ask, sizes with fractional Kelly on the edge,
   reserves in the vault, places the order, records the fill, and publishes
   `TRADE_RESULT` with outcome `pending`.
6. At `CYCLE_END` the Hand reviews open positions against the exit policy.

## The bus

`core/bus.py`. `publish` awaits every subscriber, so a handler's runtime is
inherited by whoever published. Two consequences shaped the code: work that
does not need a result is scheduled with `fire_and_forget` rather than
awaited, and a subscriber that publishes its own topic would never return --
the bus detects re-entrancy, drops the nested publish, and counts it.

## Persistence

`core/synapse.py` holds three SQLite-backed queues: opportunities (Senses to
Brain), executions (Brain to Hand), and errors. The error box is a safety
latch: while it holds anything, no cycle is authorised. `POST /reset` drains
it. `core/ledger.py` records every decision with the market price, the
estimate, the outcome, and -- after the Hand acts -- the stake, order id and
ticket (side, price, count). Hand's `settle_positions`, on the same
`CYCLE_END` boundary as the exit review, asks Kalshi about every fill with
no recorded settlement yet and fills it in, which is what lets realised
results actually be scored rather than staying open forever.

## Capital rules

`core/vault.py` tracks balance, reservations, a hard floor, a kill switch
at 85% of principal, and a profit lock. `core/trading_mode.py` is the single
switch between paper and live, consulted only inside
`KalshiClient.place_order`; it also keeps the paper position book so the
stacking guard and exit review can see simulated holdings, mirrored to
`GHOST_VAULT_DB` on every change and reloaded at boot so a restart does not
forget what paper trading is holding.

`trading_mode` also keeps a paper bankroll, seeded once from real Kalshi
cash and from then on debited by paper buys and credited by paper sells and
settlement payouts -- the real balance never moves for a paper trade, so
this is what has to track paper P&L instead. `GhostEngine.authorize_cycle`
feeds the vault this bankroll on a paper cycle rather than the real balance
(`is_paper_trading` says which), so Kelly sizing and the hard floor gate on
what paper trading has actually spent. The real balance's own hard floor
check still runs every cycle regardless of mode -- that is the check that
protects the account. `RecursiveVault` tracks a separate start-of-day
baseline and profit-lock latch per mode, since the paper bankroll can carry
accumulated P&L across a restart while the real balance's baseline is only
ever this boot's figure; `update_balance(balance, is_paper_trading=...)`
picks which one a given cycle's balance is measured against. Sizing caps
are in `core/constants.py`, most env-overridable.

`agents/hand/agent.py`'s `check_exits` only reviews the book the current
cycle's mode can actually act on -- the real Kalshi account when live, the
paper book when not -- rather than merging both: paper mode cannot place a
real order (`place_order` simulates every fill while `is_live()` is false,
real position or not), so "closing" a real holding there would neither sell
it nor be free of side effects -- the simulated fill would still write into
the paper book as if it were a paper position.

## The model

`agents/brain/debate.py`. Gemini with the Google Search tool enabled.
Ungrounded, the model answers dated questions from training data with high
confidence and is often wrong; grounded, it reads current reporting and
betting lines. The prompt never includes the market price, because a model
shown the price anchors to it and the estimate becomes untestable.

## HTTP

`engine/http_api/`. Every route is listed in [`../api/README.md`](../api/README.md).
`/stream` is server-sent events carrying `LOG`, `VAULT`, `SIMULATION`,
`STATE` and `ERROR` frames formatted by `core/event_formatter.py`.

## Known constraints

- The listing endpoint is dominated by `KXMVE` combo shards; Senses filters
  by prefix and uses a server-side close-time window.
- Model ids on both Gemini and OpenRouter change often. The lists in
  `core/ai_utils.py` end in `*-latest` aliases as a floor.
- Supabase is optional telemetry with a circuit breaker; nothing a trade
  depends on lives there.
