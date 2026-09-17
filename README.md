# Sentient Alpha

An autonomous paper-trading engine for [Kalshi](https://kalshi.com) prediction
markets. Four cooperating agents scan markets, estimate probabilities with a
search-grounded language model, check the estimate against the live orderbook,
and place simulated orders under strict capital rules.

**Status:** runs a complete cycle end to end on the Kalshi demo exchange in
paper mode. It has not been shown to have a trading edge -- see
[Is the bot any good?](RUNBOOK.md#is-the-bot-any-good) before pointing it at
real money.

## How it works

```
Soul ──CYCLE_START──▶ Senses ──OPPORTUNITY──▶ Brain ──EXECUTION_SIGNAL──▶ Hand
 │ authorises          │ selects liquid      │ grounded estimate,        │ orderbook,
 │ each cycle          │ markets, 10/cycle   │ EV, edge, confidence      │ Kelly, paper fill
 └─ vault / kill switch / error box gate every cycle ──────────────────────┘
```

- **Soul** runs the cycle, checks the vault and the error box, and learns
  only from settled trades.
- **Senses** pages the Kalshi listing for liquid, tightly-quoted markets
  closing soon, keeps a 30-market buffer, and queues 10 per cycle.
- **Brain** asks Gemini with Google Search grounding for a probability (the
  market price is deliberately withheld), computes expected value and edge,
  and vetoes on confidence or edge.
- **Hand** re-reads the live orderbook, refuses stacking and thin depth,
  sizes with fractional Kelly, and places the order through one chokepoint
  that simulates fills unless live trading is explicitly armed.

Agents talk only through an in-process event bus; opportunities, execution
signals and errors persist in SQLite (the "Synapse") so a restart loses
nothing. Every decision and fill is written to a ledger for later scoring.

## Layout

```
engine/            the Python engine (see docs/architecture/README.md)
  agents/          soul/, senses/, brain/, hand/, gateway.py, base.py
  core/            bus, synapse, vault, network, trading_mode, ledger, ...
  http_api/        aiohttp routes + SSE stream on :3002
  backtest/        score the decision path against settled markets
  scripts/         preflight.py -- checks a machine before it connects
tests/             pytest suite; no network, no credentials required
docs/              architecture, API reference, history
ai-env/            instructions and personas for AI coding assistants
frontend/          React dashboard (being replaced; not covered here)
```

## Quick start

Python 3.12 (3.11 works). On Windows use an x64 interpreter: `cryptography`
has no ARM64 wheel.

```bash
python -m venv .venv
.venv/Scripts/activate            # or: source .venv/bin/activate
pip install -r engine/requirements-dev.txt
cp engine/.env.example engine/.env   # then fill it in
python engine/scripts/preflight.py   # must print "Ready."
```

Run the engine:

```bash
PYTHONPATH=engine python engine/main.py
```

Trigger a paper cycle and watch:

```bash
curl -X POST localhost:3002/trigger -H "Content-Type: application/json" -d "{\"isPaperTrading\": true}"
curl localhost:3002/health
```

The full runbook, including risk limits and what each log line means, is
[RUNBOOK.md](RUNBOOK.md).

## Tests and lint

```bash
pytest tests/ -q
ruff check engine tests
black --check engine tests
```

All three run in CI on every push. The suite needs no credentials and blocks
outbound HTTP; a test that needs the network must say so with a marker.

## Documentation

- [RUNBOOK.md](RUNBOOK.md) -- install, configure, run, stop, and what to
  watch
- [docs/architecture/README.md](docs/architecture/README.md) -- the agents,
  the bus, the queues, and the safety rails
- [docs/api/README.md](docs/api/README.md) -- every HTTP route the engine
  serves
- [docs/history/](docs/history/) -- design narratives from earlier phases
- [AGENTS.md](AGENTS.md) -- conventions for AI assistants working in this
  repository

## Safety model

Money can only move through `KalshiClient.place_order`, which returns a
simulated fill unless `trading_mode.set_live(True)` has been called for the
current cycle. `IS_PAPER_TRADING=true` in the environment pins every cycle to
paper regardless of what the API is asked. Independently of that, a cycle is
refused when the vault is below its hard floor, the kill switch is set, or
the error box holds anything -- and `/reset` is how an operator clears it.
