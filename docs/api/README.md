# HTTP API

The engine serves an aiohttp application on port 3002. Every route below is
also mounted under `/api/` (for example `/api/trigger`) so a dashboard can
proxy a single prefix. All bodies are JSON.

## Control

| Method | Route | What it does |
|---|---|---|
| `POST` | `/trigger` | Start one cycle. Body `{"isPaperTrading": true}`. Refused if a cycle is running or the engine is halted. |
| `POST` | `/cancel` | Cancel the running cycle and release reservations. |
| `POST` | `/autopilot/start` | Let Soul start a new cycle after each one completes. Body as `/trigger`. |
| `POST` | `/autopilot/stop` | Stop after the current cycle. |
| `GET` | `/autopilot/status` | Whether autopilot is on. |

## Safety

| Method | Route | What it does |
|---|---|---|
| `POST` | `/kill-switch` | Halt: no cycle will be authorised until deactivated. |
| `POST` | `/deactivate-kill-switch` | Lift the manual kill switch. |
| `POST` | `/reset` | Return the engine to a runnable state: clears the kill switch and processing flag, drains the error box, lifts a Soul lockdown. Does not stop the engine; that is what the kill switch is for. |
| `POST` | `/ragnarok` | Cancel every open order and flatten positions. |

## Observability

| Method | Route | What it does |
|---|---|---|
| `GET` | `/health` | `{"status", "agents", "cycle", "balance"}`. Note that "healthy" means the process is up, not that a cycle can run. |
| `GET` | `/env-health` | Which optional services are configured and reachable. |
| `GET` | `/synapse/queues` | Sizes of the opportunity and execution queues, with up to ten queued items from each. |
| `GET` | `/orders` | Executed orders from the decision ledger, newest first. `?limit=` caps rows (default 200). Each row carries `side`, `price_cents`, `count`, `stake_cents`, `order_id`, `settled_yes` and `pnl_cents` (null until settled). |
| `GET` | `/config` | `groups`: every editable setting (`core/settings.py` registry) with its kind, help, limits, whether it needs a restart, and its current value; secrets carry only `set` and a four-character `hint`. `runtime`: the effective limits (`paper_pinned`, `live_armed`, `kalshi_env`, `brain`, `senses`, `hand`, `vault`, `queues`). `env_file`: where saves are persisted. |
| `POST` | `/config` | Body `{"changes": {"KEY": value, ...}}`. Validated as a batch (one bad value rejects all), persisted to the engine's `.env`, applied live where the reader can be patched. Reply: `applied`, `restart_required`, `errors`, plus the fresh `config`. Requires a signed-in dashboard session or `Authorization: Bearer <GHOST_API_KEY>`. A value of `null` clears a key back to its default. |
| `POST` | `/engine/restart` | Re-execs the engine process so restart-only settings take effect. Same auth as `POST /config`. |
| `GET` | `/journal` | The durable event log (`ghost_journal.db`): every log line, estimate, verdict, fill, exit, vault reading and error, with agent, level and cycle. Filters `agent`, `topic`, `cycle`, `level`, `since_id` (pages forward, oldest first), `limit` (max 5000). |
| `GET` | `/decisions` | Every Brain judgement from the ledger, approvals and vetoes alike, newest first: price, estimate, confidence, edge, outcome, veto reason, fill and settlement. `?limit=`, `?ticker=`. |
| `GET` | `/pnl` | Balance history. |
| `GET` | `/pnl/heatmap` | Daily P&L. |
| `GET` | `/stream` | Server-sent events. Frames are `{"type": ...}` with type `LOG`, `VAULT`, `SIMULATION`, `STATE` or `ERROR`. |

## Auth

| Method | Route | What it does |
|---|---|---|
| `POST` | `/auth/login` | Body `{"password": "<AUTH_PASSWORD>"}`. The password is required for every session; an empty one is refused with 401. A `mode` field is accepted and ignored: the dashboard uses it only to decide whether it asks for paper or live cycles, and the server's `IS_PAPER_TRADING` pin has the final say. |
| `GET` | `/auth/verify` | Current session state. |
| `POST` | `/auth/logout` | Clear it. |
| `POST` | `/auth` | Legacy check used by the original dashboard. |

Routes not in the public list require `Authorization: Bearer <GHOST_API_KEY>`.
The public list is in `core/auth.py`.

## Paper vs live

The request body's `isPaperTrading` is honoured *unless* the environment
sets `IS_PAPER_TRADING=true`, which pins every cycle to paper on the server
regardless of what the client asks. In paper mode `place_order` returns a
simulated fill with an id beginning `PAPER-` and Kalshi is never contacted.
