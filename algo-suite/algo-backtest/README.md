# algo-backtest

Runs the strategy on the LEAN engine. Pipeline steps 3–4: download → transform →
score → **backtest** → analyze.

## What it does

- **Materializes** the canonical Parquet into the durable `lean-data/` execution
  store once (read-through), then reuses it across the whole backtest sweep — the
  hot path never reconverts per run (see `../docs/parquet-evaluation.md`).
- Trains the per-family **LightGBM sub-models** and the **logistic meta-learner**
  that produce the calibrated probability `p̂ₜ` — offline, via
  `scripts/train_{baseline,hybrid}_meta_learner.py`, persisted as a portable
  (pickle-free) `f7_meta_learner.json` with its training provenance embedded.
- Applies a **deterministic filter chain** (F1 trend, F2 indicator, F3 pattern,
  F4 news-context, F5 risk-guard, F6 capital management, F7 terminal threshold) that
  converts `p̂ₜ` into the trade decision, persisting every filter's contribution
  to an audit trail. Which filters run, in what order and with which parameters is
  the strategy's `config.yaml` (see Config below), never code.
- Emits, per run: `run.json` (manifest), `trades.json` (LEAN closed-trade ledger),
  `metrics.json` and LEAN's result JSON; a config.yaml-driven chain strategy
  (`baseline`, `baseline-dsha`, `hybrid`, or a `--strategies-dir` variant) also writes
  `strategy-config.json` + `strategy-config.yaml` (the fully resolved configuration,
  defaults filled in), `strategy-provenance.json` (which `config.yaml` in the `extends:`
  chain set each parameter, or `default`), `decisions.parquet` (bar-level audit, joined to
  `trades.json` by `trade_id`) and `trade-plans.json` (one record per planned entry:
  stop, take-profit and trailing levels the executor placed). Every run then ends with
  **`statement.md`**, laid out like a
  MetaTrader/MIG Bank daily or monthly confirmation (Closed Transactions, Open Trades,
  Working Orders, the two-column A/C Summary, then Performance and Parameters with
  provenance; times `YYYY.MM.DD HH:MM` UTC, prices at the quote precision the run's
  prices carry), an **`equity.png`** equity/drawdown chart, **`equity.csv`** (the chart's
  series, one row per LEAN equity sample: `time` ISO-8601 UTC, `equity`, `drawdown_pct` —
  the input of `algo-analyze equity-curves`), and a self-contained **`report.html`**
  "Account Performance" dashboard (dark theme, inline CSS + SVG, no script or external
  resource: KPI cards, equity curve, and Equity / Drawdown / Monthly Returns / Trade
  History / Parameters tabs — `report.py`), all built purely from those artifacts
  (`statement.py`) and regenerable with `algo-backtest statement --run`. The target
  `trades.parquet` schema and `parameters.txt` are not built yet
  (see `SPEC.md` §2).
- **Baseline vs hybrid** differ only by feature families (hybrid adds the news
  family); both are ML strategies with the same meta-learner.

## Inputs and outputs

| Direction | Item |
|---|---|
| In | `lean-data/` execution store (materialized from canonical Parquet); chain strategies read `src/algo_backtest/strategies/<name>/config.yaml` + their F7 model; `hybrid` also reads `parquet/events/_features/` (+ `parquet/sentiment/` when present) |
| Out | `runs/<strategy>/<stamp>/` with `run.json`, `trades.json`, `metrics.json`, `inference-inputs.json`, LEAN's result JSON, `statement.md` + `equity.png` + `equity.csv` + `report.html` (end-of-run statement, chart, its `time,equity,drawdown_pct` series and the HTML dashboard) and, for chain strategies, `strategy-config.{json,yaml}`, `strategy-provenance.json`, `decisions.parquet` and `trade-plans.json` |

## CLI

```bash
uv run algo-backtest --help
uv run algo-backtest version
# Materialize a month of canonical Parquet into the durable lean-data store
# (data timezone resolved from config — UTC for OANDA; idempotent re-runs):
uv run algo-backtest materialize --symbol EURUSD --year 2014 --month 7
# Prove the run path end to end: run the bundled smoke-trade algorithm against the
# materialized EUR/USD lean-data, parse /Results, report the closed trade (needs Docker):
uv run algo-backtest lean-smoke
# Run the baseline strategy (fast/slow SMA crossover) over a window and report the
# closed-trade count (needs materialized data + Docker):
uv run algo-backtest run --strategy baseline-ma --symbol EURUSD --from 2014-05-07 --to 2014-05-09
#   -> writes run.json + trades.json + metrics.json to runs/<strategy>/<stamp>/, prints
#      metrics: total_return=… sharpe=… max_drawdown=… hit_rate=…, then writes the
#      broker-style statement.md + equity.png + equity.csv there and prints its A/C
#      summary lines.
# Re-extract the four Chapter-4 metrics from a finished run's artifacts:
uv run algo-backtest metrics --run <results-dir>
# Regenerate statement.md + equity.png + equity.csv + report.html for a finished run (any
# run on disk, including ones that predate the statement — `algo-analyze equity-curves`
# needs the equity.csv this writes); --out DIR writes them elsewhere. Exits 2 naming the
# file when run.json / trades.json / main.json / main-order-events.json is missing or
# malformed. For a run without trade-plans.json (one that predates story 12, or a
# code-registered strategy) the S/L and T/P columns show "—" and the statement says
# "no trade plan recorded for this run":
uv run algo-backtest statement --run <results-dir> [--out DIR]
# Run a reproducible experiment (the Chapter-4 experiment contract): every run in the
# spec writes runs/experiments/<experiment>/<id>/ + one row in experiment.json (needs the
# windows materialized + Docker; re-running replaces the whole experiment tree):
uv run algo-backtest experiment run --spec experiments/baseline-smoke.yaml
# The config.yaml-driven F1-F7 chain strategies (wiring smoke tests, see Status):
uv run algo-backtest run --strategy baseline --symbol EURUSD --from 2015-08-01 --to 2016-01-31 --param cash=10000
uv run algo-backtest run --strategy hybrid   --symbol EURUSD --from 2015-08-01 --to 2016-01-31 --param cash=10000
#   cash = the account's starting deposit. A chain strategy takes no size: F6's trade plan
#   (capital_mgmt.risk_per_trade and the stop distance) sizes every order, and the executor
#   places the plan's stop, take-profit and trailing orders (story 12). The price-only
#   baselines and the engine controls keep `size` (fraction of equity per position, (0, 1]);
#   every strategy takes cash, so a control and a chain strategy are compared from the same
#   deposit (story 12, TD-65):
uv run algo-backtest run --strategy baseline-ma --symbol EURUSD --from 2015-09-01 --to 2015-09-30 --param fast=20 --param slow=60 --param size=0.5 --param cash=10000
uv run algo-backtest run --strategy random      --symbol EURUSD --from 2015-09-01 --to 2015-09-30 --param size=0.5 --param seed=42 --param cash=10000 --param entry_probability=0.02 --param exit_probability=0.05 --param long_probability=0.5
#   random's per-bar entry/exit probabilities and its BUY share (0.5 = unbiased coin) are
#   run parameters too: no behaviour number is a literal in any bundled algorithm.
#   Every filter's own parameters live in strategies/<name>/config.yaml, not here:
#   price_features (EMA/RSI/MACD periods), indicator (F2), pattern (F3), news_context
#   (F4), risk_guard (F5), capital_mgmt (F6 sizing + the A05 trade plan), meta_learner (F7
#   thresholds, regime_gate, label horizon), execution (spread, commission, min hold,
#   close_on_veto). A new
#   strategy is a new YAML, never a code change: drop
#   strategies/<name>/config.yaml (bundled) or point --strategies-dir at a folder of them;
#   a variant states only its diff via `extends:` (any depth, like compose overrides):
uv run algo-backtest run --strategy baseline-tight --strategies-dir experiments/strategies \
    --symbol EURUSD --from 2015-09-01 --to 2015-09-30 --param cash=10000
#   Every run prints `strategy[<name>] key = value  # <source>` at bootstrap (which
#   config.yaml in the extends chain set it, or `default`) and writes the same map to
#   runs/<name>/<stamp>/strategy-provenance.json next to strategy-config.{json,yaml}. To see it
#   without running:
uv run algo-backtest explain-strategy hybrid
uv run algo-backtest explain-strategy baseline-tight --strategies-dir experiments/strategies
#   hybrid first checks that GDELT event features cover every decision minute (through
#   --to + 1 day 00:00 UTC) and, if not, exits 2 printing the `algo-score events` command.
#   --model PATH runs with a different F7 model JSON (families must match the strategy).
# Train an F7 model offline (train / validation / held-out test spans):
uv run python scripts/train_baseline_meta_learner.py --from 2015-02-02 \
    --train-end 2015-06-30 --validation-end 2015-07-31 --test-end 2016-01-31
# result aggregation is now built: `uv run algo-analyze summary` (Stage F2, Spec 05)
# planned: --cv cpcv|walkforward
```

Experiment specs (the reproducible contract) live in `../experiments/*.yaml`: a named set
of runs, each pinning `strategy/symbol/from/to` and a `params` block (e.g.
`fast/slow/size/cash`; every strategy's block includes `cash`).
The schema is closed — unknown keys are rejected.

## Config

Chain-strategy definitions live in `src/algo_backtest/strategies/<name>/config.yaml`
(`baseline`; `hybrid` `extends: baseline` adding F4; `baseline-dsha` `extends: baseline`
switching F1's perception source) or in any folder passed as `--strategies-dir`. `extends:`
chains of any depth compose base-first with cycle detection; a variant's top-level keys
(including `filters:`) replace the base's, nested sections merge key by key. Per-run
strategy parameters are `--param key=value` (`cash` alone for a chain strategy — F6's
trade plan sizes each order; `cash`, the starting deposit, is common to every strategy).
Backtest settings (e.g. `markets.oanda.data_tz`, `broker.adapter`) resolve from `../conf/backtest.yaml`,
`../conf/algo.yaml` or `ALGO_*` env.

Every key of the strategy YAML, with its range, unit, default and effect, is tabulated in
[`SPEC.md` §6.4.1](SPEC.md#641-strategy-configyaml--as-shipped-schema-2-strategiespy).
The short form (`baseline`'s values in parentheses; "req." = required when the filter is
listed; every other key defaults and the effective value is written back into the run's
`strategy-config.{json,yaml}`):

| Section | Keys |
|---|---|
| top level | `schema_version` (must be 2); `extends`; `filters` (ordered list of `f1_trend` … `f7_meta_learner`); `perception_source` (`ema`); `double_smoothed_heikin_ashi.{period1 6, period2 2, higher_tf_minutes 60}` |
| `price_features` (always resolved) | `ema_fast 3`, `ema_slow 8`, `ema_higher_tf 60`, `rsi_period 14`, `macd_fast 12`, `macd_slow 26`, `macd_signal 9`, `atr_period 14` (the `atr` stop source), `swing_lookback_bars 60` (the `swing` stop source) — minute bars |
| `indicator` (F2) | `rsi_midline 50`, `macd_hist_threshold 0` |
| `pattern` (F3) | `bullish_patterns`, `bearish_patterns` (no detector is wired, F3 ABSTAINs — TD-45) |
| `news_context` (F4, req.) | `event_intensity_veto_threshold` (Goldstein mean, ≤ it vetoes; `hybrid` −0.5), `sentiment_direction_threshold` (polarity magnitude; 0.15); `null` disables a half |
| `risk_guard` (F5, req.) | `portfolio_at_risk_cap 0.10`, `daily_drawdown_limit −0.05`, `weekly_drawdown_limit −0.15` (PnL floors, ≤ 0), `max_concurrent_trades_per_account 2`, `max_leverage 30`; `null` disables a cap; a breach vetoes |
| `capital_mgmt` (F6, req.) | sizing (req.): `risk_per_trade 0.03`, `stop_loss_pips 20`, `pip_value_per_lot 10`, `lot_notional_units 100000`, `assumed_leverage 30`; A05 trade plan (defaulted): `stop_loss_shrink 0.20` (default 0), `min_stop_pips 5` (0), `min_stop_factor 1.2` (1, × `execution.broker_stop_level_pips`), `targets [{at_level_ratio 2.0, close_fraction 0.5}]` (default one full close at 2.0), `trail_stops [{at_level_ratio 0.5, to_level_ratio −0.66}]` ([]), `min_reward_risk 2.0` (null = no veto), `stop_distance_source swing` (`fixed`), `atr_multiplier 2.0` |
| `meta_learner` (F7) | `families [trend, indicator, pattern]` (+ `news` in `hybrid`); req. with F7: `theta_high 0.55`, `theta_low 0.45`, `regime_gate false`; `label_horizon_minutes 15` |
| `execution` (always resolved) | `spread_pips 1.0` (default 0; half per fill, also inside F6's target/trail levels), `commission_per_lot 0` (per side, pro rata on lot units), `min_hold_bars 0` (bars before an opposite signal may reverse), `broker_stop_level_pips 0`, `close_on_veto false` (a veto only blocks entries; `true` closes the open position at once) |

## Testing

Unit tests (the materializer encoding) run in the default gate. **Integration tests**
(`tests/integration/`) run the pinned `quantconnect/lean:17748` image via
**testcontainers** — no QuantConnect account, no `lean` CLI — using the secret-free
`tests/integration/lean-config.json`. They carry the `integration` mark and are
**excluded from `make check`** (the image is ~10 GB):

```bash
docker pull quantconnect/lean:17748   # first time only (~10 GB; otherwise the run pulls it)
uv run pytest -m integration          # smoke backtest + UTC timezone round-trip
# slow machine? bump the per-run wait: LEAN_TEST_TIMEOUT=1200 uv run pytest -m integration
```

If Docker is unavailable the suite **skips** with a clear message (it never hard-fails).

## Status

The **lean-data materializer** (`leandata.py` + `materialize.py`) and the
`algo-backtest materialize` CLI are implemented: a month of canonical Parquet is
materialized into the durable `lean-data/` store, with the per-market data timezone
resolved from config (`config.py` → `algo_core.config.resolve`; UTC for OANDA), and
re-runs are idempotent. A testcontainers integration harness empirically nailed the
LEAN forex timezone (UTC, START-indexed — see `SPEC.md` §3.1); the earlier **LEAN
spike** (`spikes/lean/`) de-risked the path and is superseded by this committed code.
The run path is proven end to end: `lean_runner.run_lean` runs the pinned LEAN
container (`lean_runner.py`), `results.parse_results` reads `/Results` into a minimal
`RunResult(success, closed_trades, …)`, and `algo-backtest lean-smoke` ties materialize
→ run → parse together. On top of that, `algo-backtest run --strategy baseline-ma`
runs a deterministic **fast/slow SMA crossover** (long-only, single position, fixed
sizing) over a window via `run.py`, with inputs validated up front. A small **strategy
registry** (`run.py`) lets a second strategy plug into the same run path with its own
closed parameter set — **`baseline-meanrev`**, an SMA mean-reversion (counter-trend)
baseline, is the second one. Both are **price-only** rule baselines, distinct from the
F1-F7 chain strategies (`baseline`, `hybrid`) described below. Each run persists
raw artifacts (`run.json` manifest + `trades.json` ledger + `metrics.json` alongside
LEAN's result JSON, `artifacts.py`, written from a single parse of the result JSON — the
sweep never re-reads it) and reports the **first four Chapter-4 metrics** — total return,
Sharpe, max drawdown, hit rate — extracted from LEAN's portfolio statistics (`metrics.py`,
fail-fast with a remediation hint if a result has no statistics; `algo-backtest metrics
--run <dir>` reads the persisted `metrics.json`). Integration tests confirm a real run
yields a closed trade plus artifacts, and that a flat (no-trade) run reports **exactly**
zero return and zero drawdown — anchoring the LEAN-to-thesis metric mapping on a real
engine result, not a synthetic fixture. On top of the single run,
`algo-backtest experiment run --spec <yaml>` executes a **reproducible experiment**
(`experiment.py`): a closed-schema spec of named runs (`../experiments/*.yaml`), each
executed into a deterministic `runs/experiments/<experiment>/<run_id>/` (the whole
experiment tree replaced on re-run) with one flat row per run in `experiment.json` — the
seed for the Chapter-4 comparison table. A failed run aborts the experiment and writes
`experiment-error.json` instead of a manifest (exactly one of the two ever exists). An
integration tests run a one-run experiment on the real engine for **both** registered
strategies (baseline-ma and baseline-meanrev), proving the multi-strategy comparison path
(Stage F3). Result aggregation into the Chapter-4 table is done in **algo-analyze**
(`algo-analyze summary`, Stage F2 — merged). LEAN runs **locally** (Apache 2.0); no
QuantConnect cloud cost.

**Chain strategies (Spec 04h).** `run --strategy baseline` (F1+F2+F3+F5+F6+F7) and
`run --strategy hybrid` (the same chain plus F4/news) run the config.yaml-driven filter
chain inside the real pinned LEAN container: `algos/{baseline,hybrid}/main.py` are thin
subclasses of `engine/chain_algorithm.py` (shared LEAN glue), with the LEAN-free logic
in `chain/wiring.py`. `chain/decision_recorder.py` writes `decisions.parquet`, whose
`trade_id` joins `trades.json` (LEAN's ledger configured flat-to-flat). F7 models are
trained offline by `scripts/train_*_meta_learner.py` over LEAN's delivered bar stream
(`training.py`, `market_hours.py`), with train/serve feature parity proven in real LEAN.
The bundled models were trained on EUR/USD 2015-02-02 → 2015-07-31 (train +
validation), holding out 2015-08-01 → 2016-01-31. Since stories 09 and 12 (2026-09-27)
every filter parameter is a `config.yaml` section with provenance, F5's caps and F6's
economics come from the YAML (no placeholder constants remain), F6 builds the fx-manager
A05 trade plan (stop, lot, targets, trailing steps, reward:risk veto) and the executor
places it as stop-market and limit orders with configured spread and commission on every
fill (`engine/trade_plan.py`, `engine/costs.py`). Since story 13 the F3 pattern input can
be populated by the TA-Lib detector (`pattern.detector: talib`, disabled for frozen legacy
models, which need a freshly trained F7 model) and a relative quote-activity veto is
available. These runs are still **not a methodology result**: F4's sentiment half is
best-effort (TD-48), and the registered one-year protocol
(`docs/stories/in-progress/12-execution-realism/spec.md`) lost about 88% for both
strategies (story 13 evidence); see `docs/ch04-deliverables.md`. Still planned: CPCV
(`--cv`), the `trades.parquet` schema and `parameters.txt`; read-through caching.

Spec: [`SPEC.md`](SPEC.md).

### Closed-bar candlestick and quote-activity experiments

The [Heikin-Ashi comparison plan](../experiments/heikin-ashi-signals/README.md) fixes an
exploratory 2×2 comparison: TA-Lib disabled/enabled × quote-activity veto off/on.
`price_features.bar_minutes` sets complete UTC-anchored decision bars (1 by default,
60 for H1, 240 for H4); indicator periods count these bars. Multi-minute decisions
currently require EMA perception. Position stops and exits still run every minute.

`pattern.detector: talib` recognizes bullish/bearish engulfing, hammer,
shooting star, morning star and evening star from closed bid/ask midpoint OHLC.
Opposing simultaneous labels abstain; same-direction ties choose the first label
alphabetically, not the largest score. TA-Lib scores are not probabilities.

Add `volume_strength` to the filter list and its explicit configuration section to
enable the separate veto: `lookback: 20`, `min_relative_activity: 1.0`. Strength is
the current closed bar's tick count divided by the prior 20 complete bars' mean.
Warm-up or zero denominator vetoes. Counts come from canonical M1 Parquet;
missing real-bar evidence fails rather than substituting LEAN QuoteBar volume.
This measures quote activity, **not centralized FX traded volume**.

Changing the detector or decision-bar duration requires retraining F7; incompatible
models are rejected. The experiment runner archives source/configuration hashes and
every filter's effective parameters alongside successful and failed outcomes.

### Double-smoothed Heikin-Ashi perception ablation

`baseline-dsha` inherits `baseline` and selects
`perception_source: double_smoothed_heikin_ashi` in its strategy `config.yaml`.
The default source remains `ema`. The optional `double_smoothed_heikin_ashi`
mapping accepts integer `period1` (default 6), `period2` (2), and
`higher_tf_minutes` (60, must exceed the one-minute subscription).

The candidate uses a native LEAN `PythonIndicator`, composing four Wilder moving
averages, a Heikin-Ashi transform, and four linear-weighted moving averages.
Direction comes from the reordered near/far extremes: **far >= near means down,
including ties**. This intentionally preserves the historical classifier even
though its sign can be counterintuitive. Pass 2 uses the MT4 default 2; the later
Java implementation's period 1 is not this default. The first ready smoothed
candle seeds HA open at `(open + close) / 2`; both smoothing passes must be ready.
Forex QuoteBar midpoint OHLC is converted to TradeBars and fed through LEAN's
`TradeBarConsolidator`; only completed higher-timeframe bars affect direction.

No chain decision is made until both timeframes are ready. The candidate changes
only `trend_direction` and `higher_tf_trend_direction`; `trend_strength` remains
the existing EMA-gap proxy. `baseline-dsha` deliberately uses the same frozen,
EMA-trained F7 model as `baseline`. Its committed ablation is a frozen-model input
ablation, **not a retrained-model comparison**. Offline training supports both
sources through the same resolved strategy config; this does not replace the
shared frozen model automatically.
The shared chain engine also honors this selector for `hybrid` strategy configs.

Run the paired experiment with `experiments/double-smoothed-heikin-ashi.yaml`, or
run `algo-backtest run` separately with `--strategy baseline` and
`--strategy baseline-dsha`, the same window and `--param cash=10000`. Pass the two
result IDs to `algo-analyze ablation --runs <ema-id> --runs <dsha-id>`.

Implementation follows QuantConnect's [custom indicator contract](https://www.quantconnect.com/docs/v2/writing-algorithms/indicators/custom-indicators)
and [native consolidator](https://github.com/QuantConnect/Lean/blob/master/Common/Data/Consolidators/TradeBarConsolidator.cs).
The indicator is manually updated and publishes `current`/`on_updated`; do not
also register it for automatic updates. LEAN streaming initialization and session
boundaries can differ from the original MT4 historical-array calculations.

### Training the DSHA candidate

`build_training_rows(..., perception=config.perception)` uses the resolved
strategy selector and periods. The default remains EMA. DSHA training uses a pure
Python Wilder → HA → LWMA replay over the same delivered/fill-forward bar stream.
Higher-timeframe buckets use OANDA exchange-local wall time, and rows wait for
both timeframes to become ready. Native parity scenarios compare every decision
bar and feature with real LEAN, including gaps, flat ties, and custom periods.

From `algo-suite/algo-backtest`, use the existing baseline trainer with the
candidate config and a separate output artifact:

```sh
uv run python scripts/train_baseline_meta_learner.py --strategy baseline-dsha \
  --symbol EURUSD --from 2015-02-02 --train-end 2015-06-30 \
  --validation-end 2015-07-31 --test-end 2016-01-31 --out /tmp/dsha-f7.json
```

`--out` is required for `baseline-dsha`; the existing default output remains for
baseline training. Both training scripts include the resolved strategy config in
model provenance. To evaluate the separately trained candidate, use
`algo-backtest run --strategy baseline-dsha --model /tmp/dsha-f7.json` with the
normal symbol/window/cash arguments and a held-out evaluation window. No new
trained model or performance claim is included in this story. Ties remain down;
ABSTAIN-on-tie is still the separate TD-61 research question.

### Resolved strategy config artifact

Chain-driven runs (`baseline`, `baseline-dsha`, `hybrid`) publish
`strategy-config.json` and, since story 12, `strategy-config.yaml` in the run
results directory during initialization — the same fully resolved
`StrategyChainConfig.raw` mapping, including inherited settings and defaults the
loader filled in, as deterministic UTF-8 JSON and as a resolved YAML document the
strategy loader accepts as-is (so a run's exact parameters can seed a new variant).
Both are published via the shared atomic writer (same-directory temporary file
followed by replace); the JSON check runs first, so a rejected value reaches neither.
Unsupported or non-finite JSON values fail explicitly before replacing an
existing artifact. Its presence records configuration, **not successful run
completion**; completed runs still require `run.json`/`metrics.json`.
Ablation QA requires and hashes the engine-written config for both runs.

`make check` includes the offline perception dependency-boundary gate.
`make check-perception` runs the full host/native coverage, CRAP and mutation
gauntlet (requires the pinned LEAN Docker image). Pure perception modules also
belong to the package's standard mutmut scope; native adapters are tested by the
Docker-backed target. See the done story's validation report for measured results.
