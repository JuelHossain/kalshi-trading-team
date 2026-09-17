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
| `GET` | `/synapse/queues` | Sizes of the opportunity, execution and error queues. |
| `GET` | `/pnl` | Balance history. |
| `GET` | `/pnl/heatmap` | Daily P&L. |
| `GET` | `/stream` | Server-sent events. Frames are `{"type": ...}` with type `LOG`, `VAULT`, `SIMULATION`, `STATE` or `ERROR`. |

## Auth

| Method | Route | What it does |
|---|---|---|
| `POST` | `/auth/login` | Body `{"mode": "demo"}` or `{"mode": "production", "password": ...}`. Production mode is rate limited to 5 attempts per minute per IP. |
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
