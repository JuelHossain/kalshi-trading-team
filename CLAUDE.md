# Working in this repository

## Commands

```bash
pip install -r engine/requirements-dev.txt   # everything, pinned
pytest tests/ -q                             # 680+ tests, no network, no creds
ruff check engine tests                      # must be clean; CI enforces it
black --check engine tests                   # line length 100
python engine/scripts/preflight.py           # validate a machine's .env
PYTHONPATH=engine python engine/main.py      # run the engine on :3002
```

Move `engine/.env` out of the way before running the suite locally; a
populated one changes what a few configuration tests see.

## Layout

- `engine/agents/` -- Soul, Senses, Brain, Hand as packages; `gateway.py`
  relays bus events to the HTTP layer; `base.py` is the shared agent base.
- `engine/core/` -- `bus` (events), `synapse` (persistent queues), `vault`
  (capital rules), `network` (Kalshi client), `trading_mode` (paper/live
  switch and paper position book), `ledger` (decisions and fills),
  `constants` (every tunable, env-overridable where it says so).
- `engine/http_api/` -- aiohttp routes; each route is also mounted under
  `/api/`. `/stream` is server-sent events.
- `tests/engine/` -- mirrors the engine layout. `conftest.py` blocks HTTP,
  isolates databases, and provides the shared `cycle` fixture.

## Rules the code depends on

- **One chokepoint for money.** Orders go through `KalshiClient.place_order`
  and nowhere else. It returns a paper fill unless live trading is armed.
- **Telemetry never raises.** Anything in `core/db.py` and the ledger logs
  and returns; an analytics failure must not stop a trade.
- **A bus subscriber must not publish the topic it handles.** `publish`
  awaits every subscriber, so that is an infinite wait. The bus drops and
  logs re-entrant publishes; do not rely on that.
- **Background work goes through `fire_and_forget`.** A bare
  `asyncio.create_task` whose result nobody holds can be garbage-collected
  mid-flight.
- **Kalshi prices are strings in dollars** (`yes_bid_dollars`, `volume_fp`,
  `orderbook_fp`). The orderbook has no asks; a NO bid at *x* is a YES ask
  at *1 - x*. `hand/execution.parse_orderbook` is the one place that knows
  this.
- **Tests must not need the network.** Supply a fake session and mark the
  test `network_internals` if it exercises `request()` itself.

## Style

PEP 8 via black (100 columns). Type hints on signatures. Google-style
docstrings that say *why*; the code already says what. When a change is
motivated by something observed live, say so in the docstring or commit.

## Before you finish

The suite green, `ruff check` clean, and the change pushed. A red suite is
never committed.
