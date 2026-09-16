# Runbook

Getting the Ghost Engine running on your own machine, in the order the steps
actually need to happen.

## Before you start

You need a machine with outbound access to `api.kalshi.co`, Python 3.12, and
Node 20+. The engine must run continuously, so a laptop that sleeps is fine for
testing and wrong for a soak test.

```bash
python3 --version   # expect 3.12.x
node --version      # expect v20 or newer
```

## 1. Install

```bash
git clone https://github.com/JuelHossain/kalshi-trading-team.git
cd kalshi-trading-team

python3 -m venv engine/venv
source engine/venv/bin/activate          # Windows: engine\venv\Scripts\activate
pip install -r engine/requirements-dev.txt

cd frontend && npm ci && cd ..
```

Versions are pinned, so this resolves to exactly what the test suite was
verified against.

## 2. Configure

```bash
cp .env.example engine/.env
```

Then edit `engine/.env`. Four values are required — the engine refuses to start
without them, deliberately:

| Variable | Where it comes from |
|---|---|
| `KALSHI_PROD_KEY_ID` | Kalshi account → API keys. **Use demo credentials first.** |
| `KALSHI_PROD_PRIVATE_KEY` | The PEM issued with that key |
| `GHOST_API_KEY` | `python -c 'import secrets; print(secrets.token_urlsafe(32))'` |
| `AUTH_PASSWORD` | `python -c 'import secrets; print(secrets.token_urlsafe(16))'` |

`GEMINI_API_KEY` is technically optional. Without it the Brain approves
nothing, so the bot runs and does nothing at all.

> **The previous password is in this repository's git history.** Choose a new
> one. Do not reuse it.

## 3. Check it before connecting anything

```bash
PYTHONPATH=engine:. pytest tests/ -q
cd frontend && npm test && cd ..
```

Expect 378 passed / 22 skipped, and 82 frontend tests passing. The 22 skips are
the tests that need live credentials; they stop skipping once `engine/.env` has
real ones.

## 4. Start the engine

```bash
source engine/venv/bin/activate
PYTHONPATH=engine:. python3 engine/main.py
```

What a healthy start looks like:

```
SOUL initialized successfully
SENSES initialized successfully
BRAIN initialized successfully
HAND initialized successfully
GATEWAY initialized successfully
HTTP Server online at http://0.0.0.0:3002
```

**If you see `KILL SWITCH ACTIVATED` immediately**, the engine could not read
your balance and defaulted to $0, which trips the kill switch. That is the
safety system working. Check the lines above it for the real error — usually
credentials or network.

## 5. Start the dashboard

In a second terminal:

```bash
./run_dashboard.sh
```

Opens on <http://localhost:5173> and proxies `/api` to the engine on `:3002`.
Log in with `AUTH_PASSWORD`.

## Paper vs live

Two separate controls, and you want to understand both before real money:

1. **Per cycle**, from the dashboard — the request carries `isPaperTrading`,
   defaulting to paper.
2. **Server-side**, `IS_PAPER_TRADING=true` in the environment — pins every
   cycle to paper regardless of what the dashboard asks for, and logs when it
   overrides.

Keep `IS_PAPER_TRADING=true` set for the entire soak. Going live should mean
changing configuration on the machine, not clicking a different button.

## Risk limits

Only two of these come from the environment. The rest are code constants, and
that distinction matters before you rely on one.

**Set in `engine/.env`:**

| Limit | Default | Meaning |
|---|---|---|
| `VAULT_PRINCIPAL_CENTS` | 30000 | $300 principal |
| `VAULT_PROFIT_THRESHOLD_CENTS` | 5000 | $50 daily profit threshold |

**Constants in `engine/core/constants.py`** — edit the file and re-run the
suite:

| Constant | Default | Meaning |
|---|---|---|
| `HARD_FLOOR_CENTS` | 25500 | $255 — below this, no trading |
| `HAND_MAX_STAKE_CENTS` | 7500 | $75 maximum per trade |
| `BRAIN_CONFIDENCE_THRESHOLD` | 0.85 | minimum AI confidence to trade |
| `BRAIN_MAX_VARIANCE` | 0.25 | above this, the trade is vetoed |

The kill switch trips at 85% of principal, computed in `RecursiveVault`.

> `engine/config.py` reads `CONFIDENCE_THRESHOLD` and `MAX_VARIANCE` from the
> environment, and nothing imports that module. Setting those variables changes
> nothing. Do not rely on them.

The hard floor and the kill switch are the same number, so the kill switch
always fires first. That is defence in depth, not a bug, but it means you will
see kill-switch messages where you might expect hard-floor ones.

## Running it for real (pm2)

```bash
npm run build
npx pm2 start ecosystem.config.cjs
npx pm2 save
npx pm2 logs sentient-alpha-engine
```

## When something is wrong

| Symptom | Cause |
|---|---|
| `AUTH_PASSWORD not configured` | Step 2 not done. Intentional — no default exists. |
| `KILL SWITCH ACTIVATED` at startup | Balance read as $0. Check credentials and network. |
| `Supabase not configured; skipping analytics` | Harmless. Supabase is optional. |
| `Gemini API key not found` | The Brain is inert. Set `GEMINI_API_KEY`. |
| `No module named 'ddgs'` | Dependencies not installed into the active venv. |
| Dashboard shows nothing | Engine not running, or not on `:3002`. |

## Is the bot any good?

The engine records every decision it makes -- approvals and rejections alike --
to `ghost_ledger.db`, and fills in the outcome once a market settles. That is
how you answer the only question that matters:

```bash
source engine/venv/bin/activate
PYTHONPATH=engine:. python3 -c "
from core.ledger import calibration, realised_edge
for b in calibration():
    print(f\"{b['bucket']:>9}  n={b['n']:4d}  said {b['predicted']:.0%}  happened {b['actual']:.0%}  gap {b['gap']:+.2f}\")
print(realised_edge())
"
```

A calibrated engine's `said` and `happened` track each other. If it says 80%
and the event happens 50% of the time, it is confidently wrong, and no amount
of work downstream of that will make it profitable. Check this before every
decision to increase size.

Settlement is not automatic yet -- call `record_settlement(ticker, settled_yes)`
as markets resolve.

## Stop

```bash
npx pm2 stop all        # or Ctrl-C if running in the foreground
```

Stopping the engine does not cancel open orders. To flush positions, use the
Ragnarok endpoint from the dashboard, which cancels every open order.
