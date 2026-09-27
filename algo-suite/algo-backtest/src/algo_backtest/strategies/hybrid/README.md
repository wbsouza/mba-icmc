# Strategy: `hybrid`

`extends: baseline`, adding F4 (news-context) and the "news" feature family. Docs/
experiments.md Experiment 2: evaluate full hybrid vs. baseline on EUR/USD — this is the
strategy Hypothesis H1 is tested against. Config: [`config.yaml`](config.yaml).

```mermaid
flowchart TB
    Start([Bar tick])
    F1["F1 — Trend-regime filter<br/>reads trend_direction, trend_strength,<br/>higher_tf_trend_direction"]
    F2["F2 — Indicator filter<br/>reads rsi, macd_hist"]
    F3["F3 — Pattern filter<br/>reads candlestick_pattern"]
    F4["F4 — News-context filter<br/>reads real GDELT event_intensity<br/>(mandatory) + per-symbol sentiment<br/>(best-effort, TD-48)"]
    F5["F5 — Risk-guard filter<br/>reads account state, positions"]
    F6["F6 — Capital-management filter<br/>reads ATR, balance, stop distance"]
    F7["F7 — Meta-learner threshold rule<br/>p_hat from trend+indicator+pattern+news"]
    Decision([Decision: BUY / SELL / HOLD<br/>+ full audit trail])
    Veto([NO_TRADE])

    Start --> F1 --> F2 --> F3 --> F4 --> F5 --> F6 --> F7 --> Decision

    F1 -. veto: direction conflict .-> Veto
    F4 -. veto: active high-risk event .-> Veto
    F5 -. veto: risk cap breached .-> Veto
    F6 -. veto: insufficient margin .-> Veto

    classDef filter fill:#dff,stroke:#066
    classDef terminus fill:#efe,stroke:#3c3
    classDef vetoed fill:#fee,stroke:#c33
    class F1,F2,F3,F4,F5,F6,F7 filter
    class Decision terminus
    class Veto vetoed
```

## Parameters

Every configurable filter owns a section of [`config.yaml`](config.yaml); the run
only takes `--param size=<fraction of equity>` and `--param cash=<starting deposit>`.
A filter listed without its section, or a section without its filter, fails fast.
Every run records the resolved values, defaults included, as `strategy-config.json`
and `strategy-config.yaml` next to its results (the YAML is ready to seed a variant).

| Filter | Section | Keys |
|---|---|---|
| F1/F2/F6/F7 features | `price_features` | `ema_fast` 3, `ema_slow` 8, `ema_higher_tf` 60, `rsi_period` 14, `macd_fast` 12, `macd_slow` 26, `macd_signal` 9, `atr_period` 14, `swing_lookback_bars` 60 (all optional; recorded in the trained model and checked by `--model`). `atr_period` is the Wilder ATR behind the `atr_pips` feature (the bar's ATR in pips); `swing_lookback_bars` the window behind `swing_low_pips` / `swing_high_pips` (pips from the close down to the window's lowest low / up to its highest high). Pips are the instrument's: LEAN's minimum price variation × 10 live, `Instrument.unit_size` offline (0.0001 on a 5-digit pair, 0.01 on JPY). F6's stop-distance sources |
| F2 indicator | `indicator` | `rsi_midline` 50, `macd_hist_threshold` 0 (optional) |
| F3 pattern | `pattern` | `bullish_patterns`, `bearish_patterns` (optional; default vocabularies) |
| F4 news context (hybrid only) | `news_context` | `event_intensity_veto_threshold`, `sentiment_direction_threshold` (`null` disables a half) |
| F5 risk guard | `risk_guard` | `portfolio_at_risk_cap`, `daily_drawdown_limit`, `weekly_drawdown_limit`, `max_concurrent_trades_per_account`, `max_leverage` (`null` disables one) |
| F6 capital management | `capital_mgmt` | `risk_per_trade`, `stop_loss_pips`, `pip_value_per_lot`, `lot_notional_units`, `assumed_leverage` (required); the A05 trade plan (story 12, all optional): `stop_loss_shrink` 0.0 in [0, 1), `min_stop_pips` 0.0, `min_stop_factor` 1.0 (≥ 1, × `execution.broker_stop_level_pips`), `targets` `[{at_level_ratio: 2.0, close_fraction: 1.0}]` (levels strictly increasing, fractions sum ≤ 1), `trail_stops` `[]` (`at_level_ratio`, `to_level_ratio`), `min_reward_risk` `null` (= off), `stop_distance_source` `fixed`\|`atr`\|`swing`, `atr_multiplier` 2.0 |
| F7 threshold rule | `meta_learner` | `families`, `theta_high`, `theta_low`, `regime_gate`, `label_horizon_minutes` 15 (optional) |
| Execution (no filter) | `execution` | `spread_pips` 0.0, `commission_per_lot` 0.0, `min_hold_bars` 0, `broker_stop_level_pips` 0.0 (all optional; the fill costs and holding rule the executor applies, story 12) |

`regime_gate: true` is the dissertation's rule (BUY needs F1's bull regime, SELL its
bear regime); `false` trades on p̂ alone. Since 2026-09-27 (story 09) the bundled
configs run with the gate off: the six-month pilot's fitted model was anti-aligned with
F1's regime on every September bar, so the gated rule never fired.

## Variants

A new strategy is a new `strategies/<variant>/config.yaml` (bundled, or in a folder
passed as `--strategies-dir`) that `extends:` this one and states only its diff — no code
change, no registry entry. `algo-backtest explain-strategy <variant>` prints every
resolved parameter with the file that set it.

## Run

```bash
algo-backtest run --strategy hybrid --symbol EURUSD --from 2024-06-01 --to 2024-06-30 --param size=0.5 --param cash=10000
```

**Status (2026-09-26):** `config.yaml`, the pure-Python chain, and `algos/hybrid/main.py`
are all real and run against the real pinned LEAN container (Spec 04h) — same wiring
smoke-test caveats as [`baseline`](../baseline/README.md), plus F4's own sentiment half
remaining best-effort pending TD-48 (full-month real article-text ingestion, ~500 GB /
~90 hours at the current adapter's throughput) — the event-veto half is real today. See
`docs/technical-debt.md`'s TD-51 and
`docs/stories/done/2026-09-26-04h-algo-backtest-hybrid-integration/RUNBOOK.md` for the
exact commands to reproduce.
