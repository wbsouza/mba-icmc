# Policy F, registered-year run — archived config and result

Archived 2026-09-28 after an external review of PR #98 found the thesis
mislabeled this run's decision cadence as H1; it was actually M1. Source
job: `/tmp/mba-fast19-window-job-1790634718` (scratch, not durable — this
file is the durable record). See `monografia/chapters/04-experimental-evaluation.tex`,
`sec:adaptive-retraining-results`, for the caveat this archive backs.

## Run identity

- `bundle_id`: `e9681f4666891b5a704668c5b294b2781f3319763cdc951c7d6dec566d407ecb`
- `policy`: F (frozen, fit once, never refit)
- `activation_boundary`: 2016-03-01T00:00:00+00:00
- `theta_low` / `theta_high`: 0.4601994989512048 / 0.5265963956183571
- `family_rows` / `combiner_rows` / `threshold_rows`: 311737 / 29825 / 28801
- Backtest window: 2016-03-01 to 2017-02-28 (the full registered year), EUR/USD, $10,000 starting cash
- `run_exit_code.txt`: `0`

## Cadence (the corrected fact)

`strategy.yaml`'s `price_features.bar_minutes: 1` — **M1**, not H1 as the
thesis originally stated. Full `price_features` block:

```yaml
price_features:
  atr_period: 14
  bar_minutes: 1
  ema_fast: 3
  ema_higher_tf: 60
  ema_slow: 8
  macd_fast: 12
  macd_signal: 9
  macd_slow: 26
  rsi_period: 14
  swing_lookback_bars: 60
```

Filters active: `f1_trend`, `f2_indicator`, `f3_pattern` (`detector: disabled`),
`f5_risk_guard`, `f6_capital_mgmt`, `f7_meta_learner` — the baseline chain, no
news filter. `meta_learner.label_horizon_minutes: 15`, `regime_gate: false`.

## Result (LEAN native `STATISTICS::` block, as reported in the thesis)

```
STATISTICS:: Total Orders 4964
STATISTICS:: Average Win 1.66%
STATISTICS:: Average Loss -0.84%
STATISTICS:: Compounding Annual Return -97.782%
STATISTICS:: Drawdown 97.900%
STATISTICS:: Expectancy -0.219
STATISTICS:: Start Equity 10000.00
STATISTICS:: End Equity 221.82
STATISTICS:: Net Profit -97.782%
STATISTICS:: Sharpe Ratio -1.499
STATISTICS:: Sortino Ratio -2.541
STATISTICS:: Probabilistic Sharpe Ratio 0.000%
STATISTICS:: Loss Rate 74%
STATISTICS:: Win Rate 26%
STATISTICS:: Profit-Loss Ratio 1.97
STATISTICS:: Portfolio Turnover 16949.24%
STATISTICS:: OrderListHash eb6ea03a275d2ec3fd8e9bd020da30dd
```

`BUNDLEPROVIDER_CLOSED_TRADES=1603` (logged 2017-03-01 00:00:00, from
`run_log.txt`).

## Executor-integrity caveat (why this is archived, not just reported)

TD-71 (`algo-suite/docs/technical-debt.md`) is a same-bar stop/target
double-fill defect that corrupts M1-cadence runs specifically over this
exact window. This run is M1, over this exact window. It exited cleanly
(`exit_code=0`) with no `trade-plans.json` inconsistency raised — but that
check lives in algo-backtest's own statement-builder step, and this run's
numbers were read directly from LEAN's native `STATISTICS::` block, not
through that step. A clean exit therefore rules out only that specific
check, not a same-bar double fill at the order-event level (unchecked
order-event linkage between stops/targets and resulting positions).

**Executor integrity for this run is unverified — not proven defective,
and not proven clean.** The $-97.782\%$ result is reported as observed.
Resolving this needs an order-event-level audit (linked stop/target pairs
per position, checked for same-bar double fills), not a re-run under
today's deadline.

## Provenance hashes (source files at `/tmp/mba-fast19-window-job-1790634718`, scratch, ephemeral)

```
28a6009c6806d6e6062b3fb2452339a6f7115fd172ebeb84567308f700fca503  strategy.yaml
c3c068f7c0cbfcf7cba238d39180c20fc3a7292d66a510daf9c1eda25ff04e9d  statistics.txt
42bf001e5b704802b1e0ac6f337ffb967b207708876668a17f7f961b6e5635e4  run_log.txt
1c6767bbe337d82c2641ccbfc482c7742facd142a4304c758e9a2205a8a84cc1  fit_result.json
```
