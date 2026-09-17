# Sentient Alpha

An autonomous trading engine for [Kalshi](https://kalshi.com) prediction
markets. Four cooperating agents scan the exchange for liquid markets, estimate
each event's probability with a search-grounded language model, compare that
estimate against the live orderbook, and place orders under strict capital
rules. Out of the box every order is simulated; live trading has to be armed
deliberately.

**Status: v1.** The engine runs a complete cycle end to end on the Kalshi demo
exchange in paper mode, with a test suite that needs no credentials and a CI
pipeline that enforces lint and formatting. What it has *not* been shown to
have is a trading edge — the honest reading of the data so far is that a
grounded model tracks the market price to within a cent or two. See
[Is the bot any good?](RUNBOOK.md#is-the-bot-any-good) before pointing it at
real money. The dashboard is being redesigned; see [Frontend](#frontend).

## What it does

```
       ┌──────────┐   PREFLIGHT    ┌──────────┐  OPPORTUNITY   ┌──────────┐  EXECUTION   ┌──────────┐
 tick ─▶   Soul   │ ─────────────▶ │  Senses  │ ─────────────▶ │  Brain   │ ───────────▶ │   Hand   │
       └──────────┘                └──────────┘                └──────────┘   SIGNAL     └──────────┘
        authorises the cycle:       pages Kalshi for            asks Gemini (search        re-reads the live book,
        vault floor, kill switch,   liquid markets closing      grounded) for a            refuses stacking and
        error box; learns only      soon; keeps a 30-market     probability with the       thin depth, sizes with
        from settled trades         buffer, queues 10/cycle     price withheld; EV, edge   fractional Kelly, fills
                                                                and confidence gates       through one chokepoint
```

1. **Soul** owns the cycle. Before each one it checks the vault's hard floor,
   the kill switch and the error box, then runs a pre-flight against Kalshi
   and the model. It records wins and losses only when a trade has settled.
2. **Senses** walks the Kalshi listing with a server-side close-time window,
   drops the combo-market shards that dominate it, keeps the 30 most liquid,
   tightly quoted markets, and hands the Brain ten per cycle without
   re-queueing anything it sent recently.
3. **Brain** drains that queue continuously. For each market it asks Gemini —
   with Google Search grounding, and with the market price deliberately
   withheld so the estimate cannot anchor to it — for a probability, then
   computes expected value and edge against the real price and vetoes below
   the confidence or edge floor. Every decision goes to a ledger.
4. **Hand** re-reads the orderbook (Kalshi quotes no asks; a NO bid at *x* is a
   YES ask at *1 − x*), refuses to stack into a market it already holds or to
   cross thin depth, sizes the position with fractional Kelly on the edge,
   reserves the stake in the vault, and places the order. At the end of the
   cycle it reviews open positions against the exit policy.

Agents communicate only through an in-process event bus. Opportunities,
execution signals and errors persist in SQLite so a restart loses nothing.

## Safety model

- **One chokepoint for money.** Every order passes through
  `KalshiClient.place_order`, which returns a simulated fill unless live
  trading has been armed for the current cycle. `IS_PAPER_TRADING=true` pins
  every cycle to paper regardless of what the API is asked.
- **Three gates before a cycle runs:** the vault must be above its hard floor,
  the kill switch must be off, and the error box must be empty. An operator
  clears the error box with `POST /reset`.
- **Capital rules in one place.** `core/vault.py` enforces the floor, trips a
  kill switch at 85% of principal, locks principal once the day's profit
  clears its threshold, and tracks reservations so a failed order releases
  its stake.
- **Paper mode keeps its own book,** so the stacking guard and the exit review
  see simulated holdings too.

## Layout

```
engine/
  agents/        soul/, senses/, brain/, hand/  — the four agents
                 gateway.py — relays bus events to the HTTP layer
                 base.py    — shared agent base (bus, ticks, logging)
  core/          bus, synapse (persistent queues), vault, network (Kalshi
                 client), trading_mode (paper/live + paper book), ledger,
                 constants (every tunable), db (optional telemetry)
  http_api/      aiohttp routes on :3002, also under /api/; /stream is SSE
  backtest/      score the decision path against settled markets
  scripts/       preflight.py — validate a machine before it connects
tests/           pytest; blocks HTTP, isolates databases, needs no secrets
docs/            architecture, HTTP API reference, design history
ai-env/          instructions and personas for AI coding assistants
frontend/        React dashboard — being replaced, see below
```

## Quick start

Python 3.11 or 3.12. On Windows use an x64 interpreter; `cryptography` has
no ARM64 wheel.

```bash
python -m venv .venv
.venv/Scripts/activate              # or: source .venv/bin/activate
pip install -r engine/requirements-dev.txt
cp engine/.env.example engine/.env  # fill in Kalshi demo keys, Gemini key, an AUTH_PASSWORD
python engine/scripts/preflight.py  # must print "Ready."
```

Run the engine:

```bash
PYTHONPATH=engine python engine/main.py
```

Drive it from another terminal:

```bash
curl -X POST localhost:3002/trigger -H "Content-Type: application/json" -d "{\"isPaperTrading\": true}"
curl localhost:3002/health
curl -N localhost:3002/stream        # live event feed
```

Autopilot (`POST /autopilot/start`) starts a new cycle after each one
completes. The full runbook — configuration, risk limits, what each log line
means, backtesting, stopping — is [RUNBOOK.md](RUNBOOK.md).

### Tuning

Everything adjustable lives in `engine/core/constants.py`; the ones an
operator is likely to touch are environment-overridable:

| Variable | Default | Meaning |
|---|---|---|
| `BRAIN_MIN_EDGE` | `0.05` | Expected profit per $1 contract required to trade. At the default the bot vetoes most markets; lower it in paper mode to exercise the order path. |
| `BRAIN_STALE_OPPORTUNITY_SECONDS` | `300` | How long a queued market may wait before the Brain refuses it. |
| `SENSES_REQUEUE_AFTER_SECONDS` | `21600` | How long a scanned market is excluded from re-queueing. |
| `BRAIN_SEARCH_GROUNDING` | `true` | Google Search grounding for estimates. Off is a comparison arm, not a mode to run in. |
| `IS_PAPER_TRADING` | unset | `true` pins every cycle to paper on the server. |
| `KALSHI_ENV` | `demo` | `demo` or `prod`. Demo credentials cannot reach the production host, and vice versa. |

## Tests and lint

```bash
pytest tests/ -q                  # ~670 tests, ~25 s, no network, no credentials
ruff check engine tests
black --check engine tests
```

All three run in CI on every push and pull request. A test that must reach
the network says so with a marker; everything else runs against fakes.

## Frontend

The React dashboard under `frontend/` is the original cockpit and is being
replaced. A new frontend is in design now and will land after v1; it will
consume the engine's HTTP and SSE interface exactly as documented in
[`docs/api/README.md`](docs/api/README.md), which is the contract between the
two. Until then the engine is fully operable from the command line and any
HTTP client, as shown above.

## Documentation

- [RUNBOOK.md](RUNBOOK.md) — install, configure, run, watch, stop
- [docs/architecture/README.md](docs/architecture/README.md) — agents, bus,
  queues, capital rails, the model and why it is grounded
- [docs/api/README.md](docs/api/README.md) — every HTTP route the engine serves
- [docs/history/](docs/history/) — design narratives from earlier phases
- [CLAUDE.md](CLAUDE.md) and [AGENTS.md](AGENTS.md) — conventions for AI
  assistants working in this repository

## License

Private. All rights reserved by the repository owner.
