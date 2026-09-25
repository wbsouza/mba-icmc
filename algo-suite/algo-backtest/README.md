# algo-backtest

Runs the strategy on the LEAN engine. Pipeline steps 3–4: download → transform →
score → **backtest** → analyze.

## What it does

- **Materializes** the canonical Parquet into the durable `lean-data/` execution
  store once (read-through), then reuses it across the whole backtest sweep — the
  hot path never reconverts per run (see `../docs/parquet-evaluation.md`).
- Trains the per-family **LightGBM sub-models** and the **logistic meta-learner**
  that produce the calibrated probability `p̂ₜ`.
- Applies a **deterministic filter chain** (trend, indicator, pattern,
  market-activity, news-context, risk-guard, capital, terminal threshold) that
  converts `p̂ₜ` into the trade decision, persisting every filter's contribution
  to an audit trail.
- Emits, per run: `trades.parquet` (ledger), `decisions.parquet` (bar-level
  audit), equity curve and `parameters.txt`.
- **Baseline vs hybrid** differ only by feature families (hybrid adds the news
  family); both are ML strategies with the same meta-learner.

## Inputs and outputs

| Direction | Item |
|---|---|
| In | canonical Parquet + `lean-data/` execution store; strategy `../conf/backtest/<strategy>.yaml` |
| Out | `runs/<run-id>/` with `trades.parquet`, `decisions.parquet`, equity curve, `parameters.txt` |

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
#   -> writes run.json + trades.json + metrics.json to runs/<strategy>/<stamp>/, and
#      prints: metrics: total_return=… sharpe=… max_drawdown=… hit_rate=…
# Re-extract the four Chapter-4 metrics from a finished run's artifacts:
uv run algo-backtest metrics --run <results-dir>
# Run a reproducible experiment (the Chapter-4 experiment contract): every run in the
# spec writes runs/experiments/<experiment>/<id>/ + one row in experiment.json (needs the
# windows materialized + Docker; re-running replaces the whole experiment tree):
uv run algo-backtest experiment run --spec experiments/baseline-smoke.yaml
# result aggregation is now built: `uv run algo-analyze summary` (Stage F2, Spec 05)
# planned: hybrid strategy (F3); --cv cpcv|walkforward
```

Experiment specs (the reproducible contract) live in `../experiments/*.yaml`: a named set
of runs, each pinning `strategy/symbol/from/to` and a `params` block (`fast/slow/size`).
The schema is closed — unknown keys are rejected.

## Config

Strategy definitions live in `../conf/backtest/<strategy>.yaml` (the filter
chain, thresholds, risk parameters). Cross-cutting from `../conf/algo.yaml` or
`ALGO_*` env.

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
baseline, is the second one. Both are **price-only**: the news/sentiment hybrid is later
work, gated on the scoring subsystem (`algo-score`) — nothing here is labelled or scored as
that AI hybrid. Each run persists
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
QuantConnect cloud cost. Still planned: the **real news/sentiment hybrid strategy**
(Stage G, gated on `algo-score` — not built here, and not to be confused with the
price-only baselines); richer analytics (CPCV, deflated Sharpe, equity curves,
`trades.parquet` schema); read-through caching.

Spec: [`SPEC.md`](SPEC.md).
