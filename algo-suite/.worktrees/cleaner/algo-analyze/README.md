# algo-analyze

Computes the metrics and statistical validation from backtest runs. Pipeline
step 5 (final): download → transform → score → backtest → **analyze**.

## What it does

- Reads `runs/<run-id>/trades.parquet` for performance metrics and
  `decisions.parquet` for bar-level forensics (joined by `trade_id`).
- Computes **deflated Sharpe** (Bailey–López de Prado), the **Monte-Carlo
  Permutation Test** (Aronson) and the usual risk-adjusted metrics (Sharpe,
  Sortino, max drawdown, hit rate, turnover).
- Produces the **ablation tables** (price-only vs +sentiment vs +events vs full
  hybrid) and the comparison against the prior-art baseline.
- Emits the figures and tables consumed by Chapter 4 of the thesis; every number
  traces back to a `run-id`, its command and `parameters.txt`.

## Inputs and outputs

| Direction | Item |
|---|---|
| In | `runs/<run-id>/trades.parquet`, `runs/<run-id>/decisions.parquet` |
| Out | metric tables, deflated-Sharpe / MCP results, ablation tables, thesis figures |

## CLI

```bash
uv run algo-analyze --help
uv run algo-analyze version
# Aggregate every successful experiment (Stage F1) into one Chapter-4 CSV — one row per
# run, fixed auditable columns. Reads runs/experiments/*/experiment.json under the data
# root; writes <data_root>/analysis/summary.csv (override with --out):
uv run algo-analyze summary
uv run algo-analyze summary --out /tmp/summary.csv
# planned CLI: deflated-Sharpe / MCP metrics; ablation tables; baseline-vs-hybrid comparison
```

The summary table columns are: `experiment, run_id, strategy, symbol, from, to, success,
closed_trades, total_return, sharpe, max_drawdown, hit_rate, run_dir`. Output is
deterministic (rows sorted by `experiment, run_id`; written atomically) so a re-run with
unchanged data yields a byte-identical CSV the thesis can import directly.

## Config (optional)

`../conf/analyze.yaml` (planned: permutation count, significance level); cross-cutting
from `../conf/algo.yaml` or `ALGO_*` env. Data root via the shared convention
(`ALGO_DATA_ROOT` > convention), like every other tool.

## Status

**Stage F2 (result aggregation) implemented:** `algo-analyze summary` (`summary.py`)
discovers every successful experiment manifest under `runs/experiments/`, validates each
run row against the closed column contract **and the producer/consumer integrity the
canonical table relies on** — fail-fast on a corrupt manifest, an inconsistent experiment
(both a manifest and an error artifact), a wrong-typed/unknown column, a row whose
`experiment` disagrees with its manifest, a non-successful (`success=false`) run, or a
duplicate `(experiment, run_id)` — and unions them into one deterministic
`analysis/summary.csv`. Failed-only experiments are skipped. This is the canonical Chapter-4 comparison table — a baseline and
a (Stage F3) hybrid run sit side by side, ready for comparison.

**Deflated Sharpe pure function implemented:** `algo_analyze.deflated.deflated_sharpe`
applies the Bailey-Lopez de Prado closed-form haircut for independent trials, is a no-op
for a single trial, and fails fast on zero-variance raw returns. CLI wiring is still
planned with the broader significance command. Still planned: Monte-Carlo Permutation
Test, ablation tables, the explicit baseline-vs-hybrid delta (and the richer
`trades.parquet`/`decisions.parquet` forensics once those exist).

Spec: [`SPEC.md`](SPEC.md).
