# Calibration experiment

Answers one question before any capital is committed:

> Over settled markets, were the model's probability estimates closer to the
> truth than the Kalshi prices it would have traded against?

If the answer is no, the strategy cannot be profitable regardless of how well
the engine is built, because there is nothing to trade on. If the answer is
yes, that justifies repairing the engine and gives a measured edge to size
against.

This package imports nothing from `engine/`. It runs while the engine is
broken, and can be deleted wholesale if the answer comes back negative.

## Prerequisites

- `GEMINI_API_KEY` in the environment or in `engine/.env`
- `aiohttp` (already an engine dependency)
- No Kalshi credentials. Market data is read from public endpoints and no
  orders are ever placed.

If the market fetch fails, check `KALSHI_API_BASE` — Kalshi has moved API
hosts before, and the default here may need updating.

## Daily loop

```bash
python research/predict.py --count 25
```

```bash
python research/settle.py
```

```bash
python research/analyze.py
```

Collect daily, settle daily, and ignore the analysis until you have 100+
settled markets. Reading the verdict early is the main way to fool yourself.

## The model

`gemini-3.8-flash` with Google Search grounding, roughly 10s per market.

Grounding is not optional. Asked from training data alone, the model priced
a Banxico market at 0.01 with 95% confidence by citing a rate decision from
the wrong year. Confidently wrong on stale data is the exact failure this
study exists to detect, so `--no-grounding` is available only as a
comparison arm, never as the main run.

Grounded, the model reads sportsbook consensus off the web and reports it
back. Whether that beats Kalshi is the open question: if Kalshi lags the
sportsbooks there is a real edge, and if it tracks them there is none.

## The two variants

`BrainAgent.run_debate` puts the current market price into the prompt. That
makes the estimate impossible to evaluate — a model shown the price will
anchor to it, and anchoring looks like accuracy without being tradeable.

- `--variant blind` (default) withholds the price. This is the real test.
- `--variant anchored` reproduces the Brain's prompt.

Running both separates genuine information from anchoring. If blind is no
better than the market but anchored looks good, the apparent skill is an
artifact of the prompt.

## Reading the output

The headline is the paired Brier difference: `market_brier - model_brier`,
positive when the model is better. Brier score is mean squared error of a
probability forecast, and the comparison is paired because both forecasters
are graded on the identical events.

| t statistic | Meaning |
|---|---|
| `t > 2` | Model beat the market. Check the P&L survives fees. |
| `-2 < t < 2` | Indistinguishable. No edge; fees make it a net loss. |
| `t < -2` | Market beat the model. Trading this loses by construction. |

The calibration table is diagnostic rather than decisive. A model that says
0.7 should be right about 70% of the time in that bucket; systematic
overconfidence shows up as realised frequencies pulled toward 0.5.

## Known limitations

These make the result optimistic, so treat a marginal positive as negative.

- **Correlated outcomes.** Fifty markets about the same election are not
  fifty independent observations. Spread collection across unrelated topics
  or the effective sample is far smaller than `n` suggests.
- **Hypothetical fills.** The P&L assumes a fill at the quoted ask. It
  ignores slippage, market impact, and resting orders that never fill.
- **Approximate fees.** `FEE_COEFFICIENT` in `analyze.py` encodes roughly
  `ceil(0.07 x contracts x price x (1 - price))`. Verify against Kalshi's
  current published schedule before trusting the net figure.
- **Survivorship in selection.** Filtering to liquid, tight-spread markets
  selects exactly the markets that are hardest to beat. That is deliberate —
  they are also the only ones where the price means anything.

## Tests

```bash
pytest research/
```

The collectors are disposable glue and are not tested. The scoring functions
are, because a bug there produces a confident wrong answer to the only
question this exists to settle.
